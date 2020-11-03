mkdir -p tests/data

dd if=/dev/urandom of=tests/data/small.txt bs=KB count=1
dd if=/dev/urandom of=tests/data/medium.txt bs=MB count=1
dd if=/dev/urandom of=tests/data/large.txt bs=MB count=100
