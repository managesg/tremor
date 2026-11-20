import AllocScore

/-- Reads one JSON input on stdin and prints the score JSON on stdout.
Malformed input: a message on stderr and exit code 2, never a score. -/
def main : IO UInt32 := do
  let input ← (← IO.getStdin).readToEnd
  match AllocScore.run input with
  | .ok out =>
    IO.println out
    pure 0
  | .error msg =>
    IO.eprintln s!"allocscore: rejected input: {msg}"
    pure 2
