# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os
import hashlib

def get_files(base_path):
    '''takes path as string, returns tuple

    finds files one dir deep,
    tup is formatted [('Dir1', ['File1.zip', 'File2.html']), ...]'''
    staging = []
    for d in sorted(os.listdir(base_path)):
        if os.path.isdir(os.path.join(base_path,d)):
            z = [ f for f in sorted(os.listdir(os.path.join(base_path,d)))
                        if f.endswith('.zip') or f.endswith('.html') ]
            if z: # no empty dirs
                staging.append((d,z))
    return staging

def get_files_with_sums(base_path):
    '''takes path as string, returns tuple

    finds files one dir deep,
    tup is formatted [('Dir1', [('File1.zip', '8b2dc26b...'), ('file1.html', None)])]
    zips get md5sums, html files dont'''
    staging = []
    for d in sorted(os.listdir(base_path)):
        if os.path.isdir(os.path.join(base_path,d)):
            z = []
            for f in sorted(os.listdir(os.path.join(base_path,d))):
                if f.endswith('.zip'):
                    z.append((f, get_md5sum(os.path.join(base_path,d,f))))
                elif f.endswith('.html'):
                    z.append((f, None))
            if z: # no empty dirs
                staging.append((d,z))
    return staging

def get_md5sum(filename):
    '''take string filename, returns hex md5sum as string'''
    md5 = hashlib.md5()
    with open(filename,'rb') as f:
        for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
            md5.update(chunk)
    return md5.hexdigest()
