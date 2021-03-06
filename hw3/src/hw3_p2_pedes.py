""" Code for HW3 part 2 pedestrian detection

Author: Shawn Lin (shawnlin@bu.edu)
        Alex Wong (awong1@bu.edu)
"""

import os, sys
import time
import re

import cv2
import numpy as np

cv2.namedWindow("Orig_video")

# Constants
SCALE_FACTOR = 2
FPS = 10
DEBUG = False

# Parse frame ID from file name 
def get_frame_id(fn):
    return int(re.sub(r".*?frame_(\d+)\.jpg", "\\1", fn))

# Get an unused new color
def get_next_new_color(usedColors):
    newColor = (np.random.choice(range(256), size=3))
    while np.any([np.all(uc == newColor) for uc in usedColors]): # if newColor matches any of the oldColors
        newColor = (np.random.choice(range(256), size=3))
    return newColor

def get_average_video_frame(video_dir):
    """ Compute the average video frame.
    
        video_dir -- name of the video directory
    """
    frames = []
    for _, _, file_list in os.walk(video_dir):
        file_list = sorted(file_list, key=lambda x: get_frame_id(x))

        for fn in file_list:
            frame = cv2.imread("%s/%s" % (video_dir, fn), cv2.IMREAD_COLOR)
            new_shape = (frame.shape[1]//SCALE_FACTOR, frame.shape[0]//SCALE_FACTOR)
            frame = cv2.resize(frame, new_shape)
            frames.append(frame)
        print("shape", np.array(frames).shape)
        avg_frame = np.average(np.array(frames).astype(np.uint32), axis=0).astype(np.uint8)
        print(np.max(avg_frame), np.min(avg_frame))
        print("avg shape", avg_frame.shape)
        return avg_frame

def video_frame_iterator(video_dir, debug):
    """ Parse and traverse all the files in the directory and return a generator
        object of frames.
    
    Arguments:
        video_dir -- directory name that contains all the frames
        debug -- debug flag (freeze on first frame if set to True)
    """
    for _, _, file_list in os.walk(video_dir):
        file_list = sorted(file_list, key=lambda x: get_frame_id(x))

        if debug:
            while True:
                frame = cv2.imread("%s/%s" % (video_dir, file_list[0]), cv2.IMREAD_COLOR)
                new_shape = (frame.shape[1]//SCALE_FACTOR, frame.shape[0]//SCALE_FACTOR)
                frame = cv2.resize(frame, new_shape)
                yield (0, frame)
        else:
            for fn in file_list:
                time.sleep(1./FPS)
                frame = cv2.imread("%s/%s" % (video_dir, fn), cv2.IMREAD_COLOR)
                new_shape = (frame.shape[1]//SCALE_FACTOR, frame.shape[0]//SCALE_FACTOR)
                frame = cv2.resize(frame, new_shape)
                yield (get_frame_id(fn), frame)

if __name__ == "__main__":


    template_names = [
        "./img/p2/pedes_template1.png",
        "./img/p2/pedes_template2.png",
        "./img/p2/pedes_template3.png",
    ]
    templates = []

    # Preprocess templates
    for i, fn in enumerate(template_names):
        template = cv2.imread(fn, 0)
        _, template = cv2.threshold(template, 1, 255, cv2.THRESH_BINARY)
        templates.append(template)

    # Get average frame
    avg_frame = get_average_video_frame("../CS585-PeopleImages/")
    if DEBUG:
        cv2.imshow("AvgFrame", avg_frame)
        print(avg_frame.shape)

    # Keep track of previous frame
    prev_frame = np.zeros((avg_frame.shape[0], avg_frame.shape[1], 3), np.uint8)

    for frame_id, frame in video_frame_iterator("../CS585-PeopleImages/", DEBUG):

        # Remove background bias
        frame_diff = cv2.absdiff(frame, avg_frame)
        motion_diff = cv2.absdiff(frame_diff, prev_frame)
        # Currently only diff previous frame
        prev_frame = frame_diff # TODO: track multiple previous frames (window of frames)
        bi_modal_diff = cv2.bitwise_or(frame_diff, motion_diff)
        frame_diff = cv2.cvtColor(bi_modal_diff, cv2.COLOR_BGR2GRAY)

        # Thresholding
        _, frame_th = cv2.threshold(frame_diff, 40, 255, cv2.THRESH_BINARY)
        frame_blur = cv2.GaussianBlur(frame_th, (3, 3), 0)
        _, frame_th = cv2.threshold(frame_blur, 80, 255, cv2.THRESH_BINARY)
        
        # Flood filling
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(frame_th, 4, cv2.CV_32S)

        # Pedestrian detection heuristics & BBox drawing
        person_cnt = 0
        for stat in stats[1:]:
            x, y, w, h = stat[:4]
            ratio = h/w
            if ratio < 0.9 or stat[4] < 50.:
                continue

            max_match_score = 0.0
            for i, t in enumerate(templates):
                t_resize = cv2.resize(t, (w, h))
                
                obj_region = frame_th[y:y+h, x: x+w]

                res = cv2.matchTemplate(obj_region, t_resize, cv2.TM_CCOEFF_NORMED)
                res_flip = cv2.matchTemplate(obj_region, t_resize[:, ::-1], cv2.TM_CCOEFF_NORMED)

                match_score = max(res.max(), res_flip.max())
                if match_score > max_match_score:
                    max_match_idx = i
                    max_match_score = match_score

            person_cnt += 1
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 1)
            cv2.putText(frame, "%.2f" % (max_match_score), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color=(255, 0, 0)) 

        cv2.putText(frame, "Detected %i person" % (person_cnt), (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color=(0, 255, 0)) 

        cv2.imshow("Orig_video", frame)
        cv2.imshow("bi-modal_diff_video", frame_th)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            exit()
