# Why, Not Just What

The code tells you *what*.

The comment tells you *why*.

This seems obvious. And yet. How many times have you read:

```text
# Increment the counter
counter += 1
```

You do not need the comment. The code is the comment.

But this:

```text
# Skip this item if the timestamp is in the future.
# The upstream service sometimes sends speculative data.
# We drop it here rather than failing later.
if timestamp > now():
    continue
```

Now you know something the code cannot tell you. You know *why* the condition exists. You know *what the author was thinking*.

That is the real documentation. Not restating the obvious. Revealing the invisible. The assumption. The learned lesson. The bug you do not want someone to rediscover the hard way.

Write why. The what takes care of itself.
