import matplotlib.pyplot as plt
import numpy as np
import cv2
from ultralytics.yolo.utils.lane_detection_helpers import *
from ultralytics.yolo.utils.night_vision import convert_to_cv2, convert_to_torch

def canny_edges(gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2): 
            kernel_size = 5 # kernel size for Gaussian smoothing / blurring
            blur_gray= cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)#Gaussian smoothing / blurring

            # finding edges - Canny Edge detection (strong gradient between adjacent pixels)
            edges = cv2.Canny(blur_gray, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)
            return(edges)

def hough_lines(img, RHO, THETA, MIN_VOTES, MIN_LINE_LEN, MAX_LINE_GAP):
            lines = cv2.HoughLinesP(img, RHO, THETA, MIN_VOTES, np.array([]),
                                    minLineLength=MIN_LINE_LEN, maxLineGap=MAX_LINE_GAP)
            return lines

def lane_detection_core(image, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2,
                        MIN_VOTES, MIN_LINE_LEN, MAX_LINE_GAP,
                        line_color, line_thickness):

    # CANNY_THRESHOLD_1 = 50 # try: 50 - 100      # Typical: 50
    # CANNY_THRESHOLD_2 = 150 # try: 100 - 200     # Typical: 150

    #HOUGH LINES PARAMETERS
    RHO = 1                 # try: 1 - 4 (0.5 increments)  
    THETA = np.pi/180       # Usually this is Ok
    # MIN_VOTES = 70          # try: 10 - 50                  # Typical: 30
    # MIN_LINE_LEN = 70
    # MAX_LINE_GAP = 70

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    gray_img = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) # grayscale conversion

    # 5.   Get the edges (Canny)
    edges_img = canny_edges(gray_img, CANNY_THRESHOLD_1, CANNY_THRESHOLD_2)

    # 6.   Remove unwanted parts of the image (too many edges) ROI
    ROI_edges_img = helpers_masked_edges(edges_img)

    # 7.   Get the lines (from edges - Hough lines)
    lines = hough_lines(ROI_edges_img, RHO, THETA, MIN_VOTES, MIN_LINE_LEN, MAX_LINE_GAP)
    hough_lines_image = helpers_draw_lines(lines, ROI_edges_img,
                                           color= line_color,
                                           thickness= line_thickness)

    # 8.   Formulate 2 lane lines
    lanes = helpers_formulate_lanes(lines, ROI_edges_img)

    # 9.   Create an image with those 2 lines
    lanes_image = helpers_draw_lines(lanes, ROI_edges_img,
                                     color= line_color,
                                     thickness= line_thickness)

    # 10.   Combine the orginal frame with the 2 lines
    final_image = cv2.addWeighted(image, 0.8, lanes_image, 1, 0) 

    final_image = final_image[:,:,::-1]

    return final_image

# def apply_lane_detection(image):

#     image = convert_to_cv2(image)
#     image = lane_detection_core(image=image)
#     image = convert_to_torch(image)

#     return image


# img = cv2.imread(r'C:\Users\Mohamed Atef\Data Science\ITI\LaneLines-Empty\test_images\solidWhiteCurve.jpg')
# img = lane_detection_core(image=img)
# cv2.imshow('img', img)
# cv2.waitKey(0)
# cv2.destroyAllWindows()
