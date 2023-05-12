#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for owners_finder.py."""

import os
import sys
import unittest


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from testing_support import filesystem_mock

import owners_finder
import owners


ben = 'ben@example.com'
brett = 'brett@example.com'
darin = 'darin@example.com'
john = 'john@example.com'
ken = 'ken@example.com'
peter = 'peter@example.com'
tom = 'tom@example.com'


def owners_file(*email_addresses, **kwargs):
  s = ''
  if kwargs.get('comment'):
    s += '# %s\n' % kwargs.get('comment')
  if kwargs.get('noparent'):
    s += 'set noparent\n'
  s += '\n'.join(kwargs.get('lines', [])) + '\n'
  return s + '\n'.join(email_addresses) + '\n'


def test_repo():
  return filesystem_mock.MockFileSystem(files={
    '/DEPS': '',
    '/OWNERS': owners_file(ken, peter, tom),
    '/base/vlog.h': '',
    '/chrome/OWNERS': owners_file(ben, brett),
    '/chrome/browser/OWNERS': owners_file(brett),
    '/chrome/browser/defaults.h': '',
    '/chrome/gpu/OWNERS': owners_file(ken),
    '/chrome/gpu/gpu_channel.h': '',
    '/chrome/renderer/OWNERS': owners_file(peter),
    '/chrome/renderer/gpu/gpu_channel_host.h': '',
    '/chrome/renderer/safe_browsing/scorer.h': '',
    '/content/OWNERS': owners_file(john, darin, comment='foo', noparent=True),
    '/content/content.gyp': '',
    '/content/bar/foo.cc': '',
    '/content/baz/OWNERS': owners_file(brett),
    '/content/baz/froboz.h': '',
    '/content/baz/ugly.cc': '',
    '/content/baz/ugly.h': '',
    '/content/views/OWNERS': owners_file(ben, john, owners.EVERYONE,
                                         noparent=True),
    '/content/views/pie.h': '',
  })


class OutputInterceptedOwnersFinder(owners_finder.OwnersFinder):
  def __init__(self, files, local_root,
               fopen, os_path, glob,
               disable_color=False):
    super(OutputInterceptedOwnersFinder, self).__init__(
      files, local_root, None,
      fopen, os_path, glob, disable_color=disable_color)
    self.output = []
    self.indentation_stack = []

  def resetText(self):
    self.output = []
    self.indentation_stack = []

  def indent(self):
    self.indentation_stack.append(self.output)
    self.output = []

  def unindent(self):
    block = self.output
    self.output = self.indentation_stack.pop()
    self.output.append(block)

  def writeln(self, text=''):
    self.output.append(text)


class _BaseTestCase(unittest.TestCase):
  default_files = [
    'base/vlog.h',
    'chrome/browser/defaults.h',
    'chrome/gpu/gpu_channel.h',
    'chrome/renderer/gpu/gpu_channel_host.h',
    'chrome/renderer/safe_browsing/scorer.h',
    'content/content.gyp',
    'content/bar/foo.cc',
    'content/baz/ugly.cc',
    'content/baz/ugly.h',
    'content/views/pie.h'
  ]

  def setUp(self):
    self.repo = test_repo()
    self.root = '/'
    self.fopen = self.repo.open_for_reading
    self.glob = self.repo.glob

  def ownersFinder(self, files):
    return OutputInterceptedOwnersFinder(
        files,
        self.root,
        fopen=self.fopen,
        os_path=self.repo,
        glob=self.glob,
        disable_color=True,
    )

  def defaultFinder(self):
    return self.ownersFinder(self.default_files)


class OwnersFinderTests(_BaseTestCase):
  def test_constructor(self):
    self.assertNotEquals(self.defaultFinder(), None)

  def test_reset(self):
    finder = self.defaultFinder()
    for _ in range(2):
      self.assertEqual(finder.owners_queue,
                       [brett, john, darin, peter, ken, ben, tom])
      self.assertEqual(finder.unreviewed_files, {
          'base/vlog.h',
          'chrome/browser/defaults.h',
          'chrome/gpu/gpu_channel.h',
          'chrome/renderer/gpu/gpu_channel_host.h',
          'chrome/renderer/safe_browsing/scorer.h',
          'content/content.gyp',
          'content/bar/foo.cc',
          'content/baz/ugly.cc',
          'content/baz/ugly.h'
      })
      self.assertEqual(finder.selected_owners, set())
      self.assertEqual(finder.deselected_owners, set())
      self.assertEqual(finder.reviewed_by, {})
      self.assertEqual(finder.output, [])

      finder.select_owner(john)
      finder.reset()
      finder.resetText()

  def test_select(self):
    finder = self.defaultFinder()
    finder.select_owner(john)
    self.assertEqual(finder.owners_queue, [brett, peter, ken, ben, tom])
    self.assertEqual(finder.selected_owners, {john})
    self.assertEqual(finder.deselected_owners, {darin})
    self.assertEqual(finder.reviewed_by, {'content/bar/foo.cc': john,
                                          'content/baz/ugly.cc': john,
                                          'content/baz/ugly.h': john,
                                          'content/content.gyp': john})
    self.assertEqual(finder.output, [f'Selected: {john}', f'Deselected: {darin}'])

    finder = self.defaultFinder()
    finder.select_owner(darin)
    self.assertEqual(finder.owners_queue, [brett, peter, ken, ben, tom])
    self.assertEqual(finder.selected_owners, {darin})
    self.assertEqual(finder.deselected_owners, {john})
    self.assertEqual(finder.reviewed_by, {'content/bar/foo.cc': darin,
                                          'content/baz/ugly.cc': darin,
                                          'content/baz/ugly.h': darin,
                                          'content/content.gyp': darin})
    self.assertEqual(finder.output, [f'Selected: {darin}', f'Deselected: {john}'])

    finder = self.defaultFinder()
    finder.select_owner(brett)
    self.assertEqual(finder.owners_queue, [john, darin, peter, ken, tom])
    self.assertEqual(finder.selected_owners, {brett})
    self.assertEqual(finder.deselected_owners, {ben})
    self.assertEqual(finder.reviewed_by,
                     {'chrome/browser/defaults.h': brett,
                      'chrome/gpu/gpu_channel.h': brett,
                      'chrome/renderer/gpu/gpu_channel_host.h': brett,
                      'chrome/renderer/safe_browsing/scorer.h': brett,
                      'content/baz/ugly.cc': brett,
                      'content/baz/ugly.h': brett})
    self.assertEqual(finder.output, [f'Selected: {brett}', f'Deselected: {ben}'])

  def test_deselect(self):
    finder = self.defaultFinder()
    finder.deselect_owner(john)
    self.assertEqual(finder.owners_queue, [brett, peter, ken, ben, tom])
    self.assertEqual(finder.selected_owners, {darin})
    self.assertEqual(finder.deselected_owners, {john})
    self.assertEqual(finder.reviewed_by, {'content/bar/foo.cc': darin,
                                          'content/baz/ugly.cc': darin,
                                          'content/baz/ugly.h': darin,
                                          'content/content.gyp': darin})
    self.assertEqual(finder.output, [f'Deselected: {john}', f'Selected: {darin}'])

  def test_print_file_info(self):
    finder = self.defaultFinder()
    finder.print_file_info('chrome/browser/defaults.h')
    self.assertEqual(finder.output, ['chrome/browser/defaults.h [5]'])
    finder.resetText()

    finder.print_file_info('chrome/renderer/gpu/gpu_channel_host.h')
    self.assertEqual(finder.output,
                     ['chrome/renderer/gpu/gpu_channel_host.h [5]'])

  def test_print_file_info_detailed(self):
    finder = self.defaultFinder()
    finder.print_file_info_detailed('chrome/browser/defaults.h')
    self.assertEqual(finder.output,
                     ['chrome/browser/defaults.h',
                       [ben, brett, ken, peter, tom]])
    finder.resetText()

    finder.print_file_info_detailed('chrome/renderer/gpu/gpu_channel_host.h')
    self.assertEqual(finder.output,
                     ['chrome/renderer/gpu/gpu_channel_host.h',
                       [ben, brett, ken, peter, tom]])

  def test_print_comments(self):
    finder = self.defaultFinder()
    finder.print_comments(darin)
    self.assertEqual(finder.output,
                     [f'{darin} is commented as:', ['foo (at content)']])


if __name__ == '__main__':
  unittest.main()
