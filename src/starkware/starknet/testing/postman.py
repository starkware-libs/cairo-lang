from starkware.eth.eth_test_utils import EthContract, EthTestUtils
from starkware.starknet.testing.contracts import MockStarknetMessaging
from starkware.starknet.testing.starknet import Starknet


class Postman:
    def __init__(
        self,
        mock_starknet_messaging_contract: EthContract,
        starknet: Starknet,
    ):
        self.mock_starknet_messaging_contract = mock_starknet_messaging_contract
        self.starknet = starknet
        self.n_consumed_l2_to_l1_messages = 0

        # Create a filter to collect LogMessageToL2 events.
        w3_contract = self.mock_starknet_messaging_contract.w3_contract
        self.message_to_l2_filter = w3_contract.events.LogMessageToL2.createFilter(
            fromBlock="latest"
        )

    @classmethod
    async def create(cls, eth_test_utils: EthTestUtils):
        mock_starknet_messaging_contract = eth_test_utils.accounts[0].deploy(
            MockStarknetMessaging, 0
        )
        starknet = await Starknet.empty()
        return cls(
            mock_starknet_messaging_contract=mock_starknet_messaging_contract, starknet=starknet
        )

    async def _handle_l1_to_l2_messages(self):
        for event in self.message_to_l2_filter.get_new_entries():
            args = event.args

            await self.starknet.send_message_to_l2(
                from_address=int(args["fromAddress"], 16),
                to_address=args["toAddress"],
                selector=args["selector"],
                payload=args["payload"],
                nonce=args["nonce"],
            )

            self.mock_starknet_messaging_contract.mockConsumeMessageToL2.transact(
                int(args["fromAddress"], 16),
                args["toAddress"],
                args["selector"],
                args["payload"],
                args["nonce"],
            )

    def _handle_l2_to_l1_messages(self):
        l2_to_l1_messages_log = self.starknet.state.l2_to_l1_messages_log
        assert len(l2_to_l1_messages_log) >= self.n_consumed_l2_to_l1_messages
        for message in l2_to_l1_messages_log[self.n_consumed_l2_to_l1_messages :]:
            self.mock_starknet_messaging_contract.mockSendMessageFromL2.transact(
                message.from_address, message.to_address, message.payload
            )
            self.starknet.consume_message_from_l2(
                from_address=message.from_address,
                to_address=message.to_address,
                payload=message.payload,
            )
        self.n_consumed_l2_to_l1_messages = len(l2_to_l1_messages_log)

    async def flush(self):
        """
        Handles all messages and sends them to the other layer.
        """
        # Need to handle L1 to L2 first in case that those messages will create L2 to L1 messages.
        await self._handle_l1_to_l2_messages()
        self._handle_l2_to_l1_messages()
