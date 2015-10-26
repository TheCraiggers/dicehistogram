import cv2
import numpy

import PIL
import PIL.Image
import PIL.ImageChops
import PIL.ImageDraw

import collections
import json
import os

import common

MATCH_COUNT_THRESHOLD = 40

# Edge size for the otherwise unaltered image in the summary image.
SUMMARY_MEMBER_IMAGE_SIZE = 150
SUMMARY_MAX_MEMBERS = 50


class ImageComparison(object):
  detector = cv2.AKAZE_create()
  matcher = cv2.BFMatcher(cv2.NORM_HAMMING)

  def __init__(self, in_filename):
    self.filename = in_filename
    self.image = PIL.Image.open(in_filename).resize(
        (SUMMARY_MEMBER_IMAGE_SIZE, SUMMARY_MEMBER_IMAGE_SIZE))
    cv_image = cv2.imread(in_filename, 0)
    if cv_image is None:
      raise RuntimeError('OpenCV could not open %s' % in_filename)
    self.features, self.descriptors = self.detector.detectAndCompute(
        cv_image, None)
    self.match_count = 0


def FilterMatches(features_a, features_b, raw_matches, ratio=0.75):
  matching_features_a, matching_features_b = [], []
  for m in raw_matches:
    if len(m) == 2 and m[0].distance < m[1].distance * ratio:
      matching_features_a.append(features_a[m[0].queryIdx])
      matching_features_b.append(features_b[m[0].trainIdx])
  p1 = numpy.float32([kp.pt for kp in matching_features_a])
  p2 = numpy.float32([kp.pt for kp in matching_features_b])
  return p1, p2, zip(matching_features_a, matching_features_b)


def AssignToCluster(in_filename, clusters):
  image = ImageComparison(in_filename)
  best_match_count = 0
  best_members = None
  for representative, members in clusters:
    raw_matches = ImageComparison.matcher.knnMatch(
        image.descriptors,
        trainDescriptors=representative.descriptors,
        k=2)
    p1, p2, matching_feature_pairs = FilterMatches(
        image.features, representative.features, raw_matches)
    match_count = min(len(p1), len(p2))
    """
    if len(p1) >= 4:
      unused_homography, matched_points = cv2.findHomography(
          p1, p2, cv2.RANSAC, 5.0)
      match_count = numpy.sum(matched_points)  # inliers
    print '%s match %s = %d' % (
         image.filename, representative.filename, match_count)
    """
    if match_count > best_match_count:
      best_match_count = match_count
      best_members = members
  image.match_count = best_match_count
  if best_members is None or best_match_count < MATCH_COUNT_THRESHOLD:
    print '%s starts new cluster' % image.filename
    clusters.append((image, []))
  else:
    best_members.append(image)


def BuildClusterSummaryImage(clusters, skip_len):
  if not clusters:
    return
  large_edge = clusters[0][0].image.size[0]
  h = large_edge * len(clusters)
  w = 0
  for _, members in clusters:
    w = max(w, 1 + len(members))
  w = min(SUMMARY_MAX_MEMBERS, w)
  w *= large_edge
  summary_image = PIL.Image.new('RGB', (w, h))
  draw = PIL.ImageDraw.Draw(summary_image)
  for i, (representative, members) in enumerate(clusters):
    y = i * large_edge
    for j, member in enumerate(
        [representative] + members[:SUMMARY_MAX_MEMBERS - 1]):
      x = j * large_edge
      summary_image.paste(member.image, (x, y))
      draw.text((x, y), member.filename[skip_len:])
      draw.text((x, y + 20), 'features: %d' % len(member.features))
      draw.text((x, y + 40), 'matches: %d' % member.match_count)
    draw.text((0, y + 60), 'members: %d' % (len(members) + 1))
  return summary_image


if __name__ == '__main__':
  clusters = []
  cropped_image_names = os.listdir(common.CROPPED_DIR)
  n = len(cropped_image_names)
  try:
    for i, cropped_image_filename in enumerate(cropped_image_names):
      if not cropped_image_filename.lower().endswith('jpg'):
        continue
      print '%d/%d ' % (i, n),
      AssignToCluster(
          os.path.join(common.CROPPED_DIR, cropped_image_filename), clusters)
  except KeyboardInterrupt, e:
    print 'got ^C, early stop for categorization'

  for representative, members in clusters:
    print representative.filename, (1 + len(members))

  if clusters:
    skip_len = len(common.CROPPED_DIR) + 1
    summary_path = '/tmp/summary_image.jpg'
    print 'building summary image, will save to', summary_path
    summary = BuildClusterSummaryImage(clusters, skip_len)
    summary.save(summary_path)
    summary.show()

    data_path = '/tmp/summary_data.json'
    print 'saving summary data to', data_path
    data_summary = []
    for representative, members in clusters:
      data_summary.append(
          [representative.filename[skip_len:]]
           + [m.filename[skip_len:] for m in members])
    with open(data_path, 'w') as data_file:
      json.dump(data_summary, data_file)
