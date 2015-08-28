import sys

sys.path.append('~/mwf/gitclients/experimental-mwf/google3/blaze-bin/third_party/py/PIL/selftest.runfiles/google3/third_party/py/')

import PIL
import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw

import collections
import os

RAW_DIR = 'capture'
CROPPED_DIR = 'crop'
# All cropped images must have uniform size, for machine learning input.
EDGE_CROPPED = 310

COMPARISON_SIZE = EDGE_CROPPED / 4
DISTANCE_THRESHOLD = 230000 # (COMPARISON_SIZE**2 * 255) / 25


def TrimOutliersGetExtrema(coordinates, upper_bound_inclusive):
  coordinates.sort()
  histogram = collections.defaultdict(lambda: 0)
  for v in coordinates:
    histogram[v] = histogram[v] + 1
  histogram = sorted(histogram.items())
  drop_threshold = 0
  while histogram[-1][0] - histogram[0][0] > EDGE_CROPPED:
    drop_threshold += 1
    new_start = 0 if histogram[0][0] > drop_threshold else 1
    new_end = len(histogram) if histogram[0][0] > drop_threshold else -1
    histogram = histogram[new_start:new_end]

  low, high = histogram[0][0], histogram[-1][0]
  while high - low < EDGE_CROPPED:
    high += 1
    if high - low < EDGE_CROPPED:
      low -= 1
  if low < 0:
    high -= low
    low = 0
  elif high > upper_bound_inclusive:
    low -= (high - upper_bound_inclusive)
    high = upper_bound_inclusive

  return low, high


def ExtractSubject(in_filename, out_filename):
  print in_filename, out_filename
  image = PIL.Image.open(in_filename)
  print image.mode, image.size, image.format
  w, h = image.size

  image_data = image.getdata()
  out_image = PIL.Image.new(image.mode, image.size)

  tenths = (h * w) / 10
  matched_x = []
  matched_y = []
  for n, (r, g, b) in enumerate(image_data):
    y = n / w
    x = n % w
    if n % tenths == 0:
      print (x, y)
    if max(r, b) >= g:
      out_image.putpixel((x, y), (r, g, b))
      matched_x.append(x)
      matched_y.append(y)
    #else:
    #  out_image.putpixel((x, y), (r, g, b))

  min_x, max_x = TrimOutliersGetExtrema(matched_x, w - 1)
  min_y, max_y = TrimOutliersGetExtrema(matched_y, h - 1)
  bound = (min_x, min_y, max_x, max_y)
  print bound
  out_image = out_image.crop(bound)
  print out_image.size
  out_image.save(out_filename)


class ImageComparison(object):
  def __init__(self, image, filename):
    self.image = image
    self.filename = filename
    self.distance = None
    self.resized = self.image.convert(mode='L').resize(
        (COMPARISON_SIZE, COMPARISON_SIZE), resample=PIL.Image.BILINEAR)
    self.diff = None


def AssignToCluster(in_filename, clusters):
  image = ImageComparison(PIL.Image.open(in_filename), in_filename)
  best_members = None
  for representative, members in clusters:
    distance = FindDistance(image, representative)
    print '%s diff %s = %d' % (
        representative.filename, image.filename, distance)
    if distance < DISTANCE_THRESHOLD and (image.distance is None or distance < image.distance):
      image.distance = distance
      best_members = members
  if best_members is None:
    clusters.append((image, []))
  else:
    best_members.append(image)


def FindDistance(image, representative):
  min_diff = float('Inf')
  for r in xrange(0, 360, 10):
    abs_diff = PIL.ImageChops.difference(
        image.resized.rotate(r),
        representative.resized)
    diff_sum = sum(abs_diff.getdata())
    if diff_sum < min_diff:
      min_diff = diff_sum
      image.diff = abs_diff
  return min_diff


def BuildClusterSummaryImage(clusters):
  h = EDGE_CROPPED * len(clusters)
  w = 0
  for _, members in clusters:
    w = max(w, 1 + len(members))
  w *= EDGE_CROPPED
  summary_image = PIL.Image.new('RGB', (w, h))
  draw = PIL.ImageDraw.Draw(summary_image)
  for i, (representative, members) in enumerate(clusters):
    y = i * EDGE_CROPPED
    for j, member in enumerate([representative] + members):
      x = j * EDGE_CROPPED
      summary_image.paste(member.image, (x, y))
      draw.text((x, y), member.filename)
      if member.diff is not None:
        summary_image.paste(
            member.diff, (x, y + (EDGE_CROPPED - COMPARISON_SIZE)))
      if member.distance is not None:
        draw.text((x, y + 20), str(member.distance))
  return summary_image


if __name__ == '__main__':
  EXTRACT = 0
  CLUSTER = 1
  run_stages = (CLUSTER,)
  if EXTRACT in run_stages:
    for raw_image_filename in os.listdir(RAW_DIR):
      if not raw_image_filename.endswith('jpg'):
        continue
      ExtractSubject(
          os.path.join(RAW_DIR, raw_image_filename),
          os.path.join(CROPPED_DIR, raw_image_filename))
  if CLUSTER in run_stages:
    clusters = []
    for cropped_image_filename in os.listdir(CROPPED_DIR):
      if not cropped_image_filename.endswith('jpg'):
        continue
      AssignToCluster(
          os.path.join(CROPPED_DIR, cropped_image_filename), clusters)
    BuildClusterSummaryImage(clusters).save('/tmp/summary_image.jpg')
