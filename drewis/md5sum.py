# Stack Overflow
import hashlib

def get(filename):
    '''take string filename, returns hex md5sum as string'''
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()
