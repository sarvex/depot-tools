#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import subprocess
import sys
import urllib

IS_WIN = sys.platform.startswith('win')
BASE_URL = 'http://src.chromium.org/svn/trunk/tools/buildbot/scripts/'
COMPILE_URL = f'{BASE_URL}slave/compile.py'
UTILS_URL = f'{BASE_URL}common/chromium_utils.py'


def Fetch(url, filename):
  if not os.path.exists(filename):
    urllib.urlretrieve(url, filename)


def GetLastestRevision():
  """Returns the revision number of the last build that was archived, or
  None on failure."""
  url = 'http://build.chromium.org/buildbot/continuous/'
  if sys.platform.startswith('win'):
    url += 'win/'
  elif sys.platform.startswith('linux'):
    url += 'linux/'
  elif sys.platform.startswith('darwin'):
    url += 'mac/'
  url += 'LATEST/REVISION'
  if text := urllib.urlopen(url).read():
    if match := re.search(r"(\d+)", text):
      return int(match[1])
  return None


def DoUpdate(chrome_root):
  """gclient sync to the latest build."""
  cmd = ["gclient", "sync"]
  if rev := GetLastestRevision():
    cmd.extend(['--revision', 'src@%d' % rev])
  return subprocess.call(cmd, cwd=chrome_root, shell=IS_WIN)


def DoBuild(chrome_root, args):
  """Download compile.py and run it."""
  compile_path = os.path.join(chrome_root, 'compile.py')
  Fetch(COMPILE_URL, compile_path)
  Fetch(UTILS_URL, os.path.join(chrome_root, 'chromium_utils.py'))
  cmd = ['python', compile_path] + args
  return subprocess.call(cmd, cwd=chrome_root, shell=IS_WIN)


def main(args):
  if len(args) < 3:
    print('Usage: chrome-update.py <path> [options]')
    print('See options from compile.py at')
    print(f'  {COMPILE_URL}')
    print('\nFor more example, see the compile steps on the waterfall')
    return 1

  chrome_root = args[1]
  if not os.path.isdir(chrome_root):
    print(f'Path to chrome root ({chrome_root}) not found.')
    return 1

  rv = DoUpdate(chrome_root)
  if rv != 0:
    print('Update Failed.  Bailing.')
    return rv

  DoBuild(chrome_root, args[2:])
  print('Success!')
  return 0


if __name__ == "__main__":
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)
