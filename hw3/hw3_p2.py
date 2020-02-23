import os, sys
import time
import re

import cv2
import numpy as np

cv2.namedWindow("Orig_video")

# Constants
SCALE_FACTOR = 4
FPS = 1

def nothing(x):
    pass

# HSV filter bar
cv2.createTrackbar("low_h", "Orig_video", 0, 255, nothing)   # 11
cv2.createTrackbar("high_h", "Orig_video", 12, 255, nothing)    # 11
cv2.createTrackbar("low_s", "Orig_video", 94, 255, nothing)  # 190
cv2.createTrackbar("high_s", "Orig_video", 178, 255, nothing)    # 190
cv2.createTrackbar("low_v", "Orig_video", 117, 255, nothing)  # 48
cv2.createTrackbar("high_v", "Orig_video", 255, 255, nothing)    # 48

def get_frame_id(fn):
    return int(re.sub(r"piano_(\d+)\.png", "\\1", fn))

def get_next_new_color(usedColors):
    newColor = (np.random.choice(range(256), size=3))
    while np.any([np.all(uc == newColor) for uc in usedColors]): # if newColor matches any of the oldColors
        newColor = (np.random.choice(range(256), size=3))
    return newColor

def get_average_video_frame(video_dir):

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

def skin_masking(frame):
    low_h = cv2.getTrackbarPos("low_h", "Orig_video")
    high_h = cv2.getTrackbarPos("high_h", "Orig_video")
    low_s = cv2.getTrackbarPos("low_s", "Orig_video")
    high_s = cv2.getTrackbarPos("high_s", "Orig_video")
    low_v = cv2.getTrackbarPos("low_v", "Orig_video")
    high_v = cv2.getTrackbarPos("high_v", "Orig_video")

    lower_range = np.array([low_h, low_s, low_v], dtype= "uint8")
    upper_range = np.array([high_h, high_s, high_v], dtype ="uint8")
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    frame = cv2.inRange(frame, lower_range, upper_range);
    
    return frame

def get_label_map(frame_th, num_labels, labels, stats, centroids):
    label_map = np.zeros((frame_th.shape[0], frame_th.shape[1], 3), np.uint8)


    # Only focus on coloring the top 3 largest object
    stats = [(i, stat) for i, stat in enumerate(stats)]
    stats = sorted(stats[1:], key=lambda x: x[1][4], reverse=True)[:2]

    color_map = [np.array([0, 0, 0])]
    for _ in range(num_labels):
        color = get_next_new_color(color_map)
        color_map.append(color)

    for i in range(labels.shape[0]):
        for j in range(labels.shape[1]):
            color_label = labels[i][j]
            if color_label in [st[0] for st in stats]:
                color = color_map[color_label]
                label_map[i][j] = color
    
    # print(label_map.shape)
    # cv2.imshow("labels", label_map)
    # cv2.waitKey(0)
    return label_map, stats
# def thresholding(method=METHOD):
#     if method == "absolute":
#         _, thresh = 
#     else:
#         thresh = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY_INV,3,1)

if __name__ == "__main__":

    debug = False    

    avg_frame = get_average_video_frame("./CS585-PianoImages")
    # cv2.imshow("AvgFrame", avg_frame)

    # cv2.waitKey(0)
    for frame_id, frame in video_frame_iterator("./CS585-PianoImages", debug):
        
        frame_diff = cv2.absdiff(frame, avg_frame)
        frame_diff = cv2.cvtColor(frame_diff, cv2.COLOR_BGR2GRAY)
        _, roi_mask = cv2.threshold(frame_diff, 10, 255, cv2.THRESH_BINARY)
        
        # cv2.imshow("mask", roi_mask)    

        frame_roi = cv2.bitwise_and(frame, frame, mask=roi_mask)

        # skin detection
        frame_gs = skin_masking(frame_roi)

        # Morphology
        frame_blur = cv2.GaussianBlur(frame_gs, (3, 3), 0)
        _, frame_th = cv2.threshold(frame_blur, 50, 255, cv2.THRESH_BINARY)
        frame_blur = cv2.GaussianBlur(frame_th, (5, 5), 0)
        _, frame_th = cv2.threshold(frame_blur, 80, 255, cv2.THRESH_BINARY)

        kernel_3x3 = np.ones((5, 5), np.uint8)
        kernel_7x7 = np.ones((3, 3), np.uint8)

        frame_gs = cv2.dilate(frame_gs, kernel_3x3, iterations=1)
        frame_gs = cv2.erode(frame_gs, kernel_3x3, iterations=1)
        frame_gs = cv2.dilate(frame_gs, kernel_7x7, iterations=1)
        frame_gs = cv2.erode(frame_gs, kernel_7x7, iterations=1)

        frame_gs = cv2.GaussianBlur(frame_gs, (3, 3), 0)
        _, frame_gs = cv2.threshold(frame_gs, 150, 255, cv2.THRESH_BINARY)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(frame_th, 4, cv2.CV_32S)
        print(num_labels)
        

        label_map, stats = get_label_map(frame_th, num_labels, labels, stats, centroids)
        cv2.imshow("labels", label_map)
        

        # Draw hand bounding box
        for stat in stats:
            x, y, w, h = stat[1][:4]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imshow("Orig_video", frame)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            exit(0)
