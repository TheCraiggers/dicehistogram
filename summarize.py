#!/usr/bin/env python
"""Stage 3: Summarize die roll data.

Example:
    %(prog)s data/myd6/ 5 6 4 1 2 1 1 3 1 2 1 6 1 1 5 1 1
where data/myd20 contains the summary.json file written by stage 2.

Positional arguments are labels for the die-roll image groupings, in the same
order as they appear in the summary data (or summary image). They are expected
to be integers. Typically the first N will name the N sides of the die, and then
additional labels will repeat labels for any stragglers.

TODO:
 - Image of histogram?
 - Sequence graph.
 - Heatmap of common polyhedrals.
"""

import argparse
import collections
import json
import numpy
import os


HISTOGRAM_BASE_LEN = 50
def PrintHistogram(labeled_file_sets):
  values = [len(filenames_set) for filenames_set in labeled_file_sets.values()]
  total = sum(values)
  np_values = numpy.array(values)
  mean = numpy.mean(np_values)
  np_values = np_values / mean

  expected_value = 0
  for label, filename_set in labeled_file_sets.items():
    normalized_value = len(filename_set) / mean
    expected_value += label * normalized_value
  expected_value = expected_value / len(labeled_file_sets)

  print 'N=%d normalized stddev=%.2f min=%.2f max=%.2f expected=%.2f' % (
      total,
      numpy.std(np_values),
      min(np_values),
      max(np_values),
      expected_value)
  for label, filename_set in sorted(labeled_file_sets.items()):
    v = len(filename_set) / mean
    i = int(v * HISTOGRAM_BASE_LEN)
    if i < HISTOGRAM_BASE_LEN:
      bar = '=' * i
    else:
      bar = ('=' * (HISTOGRAM_BASE_LEN - 1)) + '*' + (
          '=' * (i - HISTOGRAM_BASE_LEN))
    print '%4d %4.2f %s' % (label, v, bar)


if __name__ == '__main__':
  summary_line, _, main_doc = __doc__.partition('\n\n')
  parser = argparse.ArgumentParser(
      description=summary_line,
      epilog=main_doc,
      formatter_class=argparse.RawDescriptionHelpFormatter)
  parser.add_argument(
      '--summary-data', '-d', dest='summary_data',
      default='summary.json',
      help='File name for the summary data, JSON written from stage 2.')
  args, positional = parser.parse_known_args()
  data_dir = positional[0]
  labels = map(int, positional[1:])

  summary_data_filename = os.path.join(data_dir, args.summary_data)
  with open(summary_data_filename) as data_file:
    summary_data = json.load(data_file)

  if len(labels) != len(summary_data):
    print labels
    for i, l in enumerate(summary_data, start=1):
      print i, (l[:4] + ([] if len(l) <= 4 else ['...']))
    parser.error(
        ('Got %d positional argument labels but %d data groupings in summary '
         + 'data; they must match.')
        % (len(labels), len(summary_data)))

  labeled_file_sets = collections.defaultdict(lambda: set())
  for filename_list, label in zip(summary_data, labels):
    labeled_file_sets[label].update(filename_list)

  print 'Summary of', summary_data_filename
  PrintHistogram(labeled_file_sets)
