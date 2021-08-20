import pandas as pd
import cv2
import numpy as np
import math

import layout.lib.draw as draw


def calc_compos_distance(compo1, compo2):
    # compo1 is on the left of compo2
    if compo1['column_max'] <= compo2['column_min']:
        dist_h = compo2['column_min'] - compo1['column_max']
    # compo1 is on the right of compo2
    elif compo2['column_max'] <= compo1['column_min']:
        dist_h = compo1['column_min'] - compo2['column_max']
    # compo1 and compo2 align vertically
    else:
        dist_h = -1

    # compo1 is on the top of compo2
    if compo1['row_max'] <= compo2['row_min']:
        dist_v = compo2['row_min'] - compo1['row_max']
    # compo1 is below compo2
    elif compo2['row_max'] <= compo1['row_min']:
        dist_v = compo1['row_min'] - compo2['row_max']
    # compo1 and compo2 align horizontally
    else:
        dist_v = -1

    if dist_h == -1:
        # compo1 and compo2 are intersected, which is impossible as UIED has merged all intersected compoments
        if dist_v == -1:
            print('Impossible due to all intersected compos were merged')
            return False
        else:
            return dist_v
    else:
        if dist_v == -1:
            return dist_h
        # compo1 and compo2 dont align neither vertically nor horizontally
        else:
            dist = math.sqrt(dist_v ** 2 + dist_h ** 2)
            return dist


def match_angles(angles_all, max_matched_angle_diff=10):
    '''
    @angles_all : list of list, each element in the g1's angle with each element in the g2
                [[0.27, -12.88, 24.40],  # the 1st element in the g1's angles with all elements in the g2
                [13.00, 0.18, 13.06]]    # the 2ed element in the g1's angles with all elements in the g2
    Match if there are any similar angles for the 1st and 2ed element (e.g. 0.25 abd 0.18 in the example)
    '''
    for i in range(min(3, len(angles_all) - 1)):
        angles_i = angles_all[i]
        for k, an_i in enumerate(angles_i):
            # match with others
            matched_num = 1
            paired_ids = [k]
            for j in range(i + 1, len(angles_all)):
                angles_j = angles_all[j]
                for p, an_j in enumerate(angles_j):
                    if abs(an_i - an_j) < max_matched_angle_diff:
                        paired_ids.append(p)
                        matched_num += 1
                        break
            if matched_num == len(angles_all):
                return paired_ids
    return None


def match_two_groups_with_text_by_angles(g1, g2, diff_angle=10):
    '''
    As the text's length is variable, we don't count on distance if one or more groups are texts.
    In this situation, we only count on the angles of the line between two possibly paired elements.
    '''
    assert g1.iloc[0]['alignment_in_group'] == g2.iloc[0]['alignment_in_group']
    alignment = g1.iloc[0]['alignment_in_group']
    pairs = {}
    if alignment == 'h':
        g1_sort = g1.sort_values('center_column')
        g2_sort = g2.sort_values('center_column')
    else:
        g1_sort = g1.sort_values('center_row')
        g2_sort = g2.sort_values('center_row')

    swapped = False
    if len(g1) == len(g2):
        angles = []
        for i in range(len(g1_sort)):
            c1 = g1_sort.iloc[i]
            c2 = g2_sort.iloc[i]
            if c1['column_min'] >= c2['column_min']:
                angle = int(math.degrees(math.atan2(c1['row_min'] - c2['row_min'], c1['column_min'] - c2['column_min'])))
            else:
                angle = int(math.degrees(math.atan2(c2['row_min'] - c1['row_min'], c2['column_min'] - c1['column_min'])))
            # print(angles, angle)
            # compare the pair's distance and angle between the line and the x-axis
            if i > 0:
                if abs(angle - angles[i - 1]) > diff_angle:
                    return False
            pairs[c1['id']] = c2['id']
            angles.append(angle)
    else:
        # make sure g1 represents the shorter group while g2 is the longer one
        if len(g1_sort) > len(g2_sort):
            temp = g1_sort
            g1_sort = g2_sort
            g2_sort = temp
            swapped = True

        angles_all = []
        # calculate the distances between each c1 in g1 and all c2 in g2
        for i in range(len(g1_sort)):
            c1 = g1_sort.iloc[i]
            angles = []
            for j in range(len(g2_sort)):
                c2 = g2_sort.iloc[j]
                angle = math.degrees(math.atan2(c1['row_min'] - c2['row_min'], c1['column_min'] - c2['column_min']))
                angles.append(angle)
            angles_all.append(angles)

        matched_angle_pairs = match_angles(angles_all)
        if matched_angle_pairs is None:
            return False
        else:
            for i, paired_id in enumerate(matched_angle_pairs):
                pairs[g1_sort.iloc[i]['id']] = g2_sort.iloc[paired_id]['id']

    # print('Success:', g1.iloc[0]['group'], g2.iloc[0]['group'], distances, max_side)
    for i in pairs:
        if not swapped:
            g1.loc[i, 'pair_to'] = pairs[i]
            g2.loc[pairs[i], 'pair_to'] = i
        else:
            g2.loc[i, 'pair_to'] = pairs[i]
            g1.loc[pairs[i], 'pair_to'] = i
    return True


def match_two_groups_by_distance(g1, g2, diff_distance=1.2, diff_angle=10):
    assert g1.iloc[0]['alignment_in_group'] == g2.iloc[0]['alignment_in_group']
    alignment = g1.iloc[0]['alignment_in_group']
    pairs = {}
    if alignment == 'h':
        g1_sort = g1.sort_values('center_column')
        g2_sort = g2.sort_values('center_column')
        max_side = max(list(g1['height']) + list(g2['height']))
    else:
        g1_sort = g1.sort_values('center_row')
        g2_sort = g2.sort_values('center_row')
        max_side = max(list(g1['width']) + list(g2['width']))

    swapped = False
    if len(g1) == len(g2):
        distances = []
        angles = []
        for i in range(len(g1_sort)):
            c1 = g1_sort.iloc[i]
            c2 = g2_sort.iloc[i]
            distance = calc_compos_distance(c1, c2)
            angle = int(math.degrees(math.atan2(c1['center_row'] - c2['center_row'], c1['center_column'] - c2['center_column'])))
            # mismatch if too far
            if distance > max_side * 2:
                return False
            # compare the pair's distance and angle between the line and the x-axis
            if i > 0:
                if (abs(distance - distances[i-1]) > 10 and max(distance, distances[i-1]) > diff_distance * min(distance, distances[i-1])) and \
                        abs(angle - angles[i - 1]) > diff_angle:
                    return False
            pairs[c1['id']] = c2['id']
            distances.append(distance)
            angles.append(angle)
    else:
        # make sure g1 represents the shorter group while g2 is the longer one
        if len(g1_sort) > len(g2_sort):
            temp = g1_sort
            g1_sort = g2_sort
            g2_sort = temp
            swapped = True

        distances = []
        angles = []
        marked = np.full(len(g2_sort), False)  # mark the matched compo in the g2
        # calculate the distances between each c1 in g1 and all c2 in g2
        for i in range(len(g1_sort)):
            c1 = g1_sort.iloc[i]
            distance = None
            angle = None
            matched_id = None
            for j in range(len(g2_sort)):
                if marked[j]: continue
                c2 = g2_sort.iloc[j]
                d_cur = calc_compos_distance(c1, c2)
                if distance is None or distance > d_cur:
                    distance = d_cur
                    angle = math.degrees(math.atan2(c1['center_row'] - c2['center_row'], c1['center_column'] - c2['center_column']))
                    pairs[c1['id']] = c2['id']
                    # mark the matched compo
                    marked[j] = True
                    # unmark the previously matched compo
                    if matched_id is not None:
                        marked[matched_id] = False
                    matched_id = j
            distances.append(distance)
            angles.append(angle)
        # match the distances and angles
        match_num = 1
        for i in range(len(distances)):
            dis_i = distances[i]
            angle_i = angles[i]
            for j in range(len(distances)):
                if i == j:
                    continue
                dis_j = distances[j]
                angle_j = angles[j]
                # compare the pair's distance and angle between the line and the x-axis
                if max(dis_i, dis_j) < max_side * 2 and\
                        (abs(dis_i - dis_j) <= 10 or max(dis_i, dis_j) < diff_distance * min(dis_i, dis_j)) and\
                        abs(angle_i - angle_j) < diff_angle:
                    match_num += 1
                    break
        # print(g1.iloc[0]['group'], g2.iloc[0]['group'], match_num, distances, max_side)
        if match_num < min(len(g1), len(g2)) * 0.8:
            return False

    # print('Success:', g1.iloc[0]['group'], g2.iloc[0]['group'], distances, max_side)
    for i in pairs:
        if not swapped:
            g1.loc[i, 'pair_to'] = pairs[i]
            g2.loc[pairs[i], 'pair_to'] = i
        else:
            g2.loc[i, 'pair_to'] = pairs[i]
            g1.loc[pairs[i], 'pair_to'] = i
    return True


def pair_matching_within_groups(groups, start_pair_id, new_pairs=True, max_group_diff=2):
    pairs = {}  # {'pair_id': [dataframe of grouped by certain attr]}
    pair_id = start_pair_id
    mark = np.full(len(groups), False)
    if new_pairs:
        for group in groups:
            if 'group_pair' in group.columns:
                group.drop('group_pair', axis=1, inplace=True)
    for i, g1 in enumerate(groups):
        # if mark[i]: continue
        alignment1 = g1.iloc[0]['alignment_in_group']
        for j in range(i + 1, len(groups)):
            g2 = groups[j]
            alignment2 = g2.iloc[0]['alignment_in_group']
            if alignment1 == alignment2:
                # for Text, the length could be variable so cannot match through distance
                if g1.iloc[0]['class'] == 'Text' or g2.iloc[0]['class'] == 'Text':
                    if not match_two_groups_with_text_by_angles(g1, g2):
                        continue
                # if both are Compo, match through distance and angle
                else:
                    if not match_two_groups_by_distance(g1, g2):
                        continue
                # print(i, list(g1['group'])[0], mark[i], '-', j, list(g2['group'])[0], mark[j])
                if not mark[i]:
                    # hasn't paired yet, creat a new pair
                    if not mark[j]:
                        pair_id += 1
                        g1['group_pair'] = pair_id
                        g2['group_pair'] = pair_id
                        pairs[pair_id] = [g1, g2]
                        mark[i] = True
                        mark[j] = True
                    # if g2 is already paired, set g1's pair_id as g2's
                    else:
                        g1['group_pair'] = g2.iloc[0]['group_pair']
                        pairs[g2.iloc[0]['group_pair']].append(g1)
                        mark[i] = True
                else:
                    # if gi is marked while gj isn't marked
                    if not mark[j]:
                        g2['group_pair'] = g1.iloc[0]['group_pair']
                        pairs[g1.iloc[0]['group_pair']].append(g2)
                        mark[j] = True
                    # if gi and gj are all already marked in different group_pair, merge the two group_pairs together
                    else:
                        # merge all g2's pairing groups with g1's
                        if g1.iloc[0]['group_pair'] != g2.iloc[0]['group_pair']:
                            g1_pair_id = g1.iloc[0]['group_pair']
                            g2_pair_id = g2.iloc[0]['group_pair']
                            for g in pairs[g2_pair_id]:
                                g['group_pair'] = g1_pair_id
                                pairs[g1_pair_id].append(g)
                            pairs.pop(g2_pair_id)

    merged_pairs = None
    for i in pairs:
        for group in pairs[i]:
            if merged_pairs is None:
                merged_pairs = group
            else:
                merged_pairs = merged_pairs.append(group, sort=False)
    return merged_pairs


def pair_visualization(pairs, img, img_shape, show_method='line'):
    board = img.copy()
    if show_method == 'line':
        for id in pairs:
            pair = pairs[id]
            for p in pair:
                board = draw.visualize(board, p.compos_dataframe, img_shape, attr='group_pair', show=False)
    elif show_method == 'block':
        for id in pairs:
            pair = pairs[id]
            for p in pair:
                board = draw.visualize_fill(board, p.compos_dataframe, img_shape, attr='group_pair', show=False)
    cv2.imshow('pairs', board)
    cv2.waitKey()
    cv2.destroyAllWindows()

