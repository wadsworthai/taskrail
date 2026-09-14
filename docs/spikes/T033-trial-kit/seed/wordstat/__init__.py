"""Count the words in a text."""


def stats(text):
    """Return the statistics of a text, in output order."""
    words = len(text.split(" ")) if text else 0
    return {"words": words}
