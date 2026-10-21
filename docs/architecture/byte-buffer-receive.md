# ByteBuf after external writes

ByteBuf's initialized prefix is [0,len), with 0 <= len <= cap. A socket receive
writes memory but cannot mutate a value's len field. Call buf_received(buf,count)
after a successful complete receive, with the actual initialized byte count,
before bounded readers inspect it. The returned view preserves address/capacity
and sets len; it shares the original allocation, which must be freed once.

pg_read_msg publishes both header and body lengths. Error field C-string scans
therefore see the received payload. Read errors and truncation fail before
publishing incomplete data. Future external-write APIs may return updated views
directly; then this bridge can be removed with all callers migrated together.
