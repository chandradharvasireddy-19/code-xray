import hashlib


class OldMD5Hasher:
    """
    Deprecated legacy password and token hashing utility.
    No callers, imports, or test invocations exist for this class.
    """

    def hash_string(self, raw_value: str) -> str:
        """
        Produce MD5 digest (insecure, superseded by SHA-256).
        """
        return hashlib.md5(raw_value.encode("utf-8")).hexdigest()
