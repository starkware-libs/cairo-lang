def get_prev_batch_id_docstring(uri_prefix: str, port: int, batch_term: str) -> str:
    return f"""
        Get the previous {batch_term} ID for the input batch_id.

        :param batch_id: {batch_term.title()} ID to query.
        :type batch_id: int
        :return: The previous {batch_term} ID.
        :rtype: int

        :example:

        ..  http:example:: curl wget httpie python-requests

            GET {uri_prefix}/get_prev_batch_id HTTP/1.1
            Host: localhost:{port}
            Accept: application/json

            :query batch_id: 5678


            HTTP/1.1 200 OK
            Content-Type: application/json

            5676
        """
