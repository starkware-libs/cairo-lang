import patricia.crypto

structure NodeEdge where
  length: ℕ
  path: ℕ
  bottom: ℕ

def NodeEdge.hash (edge: NodeEdge) (crypto: Crypto) : ℕ :=
  if edge.length = 0 then
    edge.bottom
  else
    (crypto.hash edge.bottom edge.path) + edge.length
