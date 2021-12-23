import base64
import collections
import math
import os
import cv2
import numpy as np
import time
import threading
np.set_printoptions(threshold=np.inf)

class ThreadingWrapper(threading.Thread): 
    def __init__(self, numPins, maxLines, lineWeight, image):
        self.stringAlg = StringAlg(numPins, maxLines, lineWeight, image)
        self.progress = 0
        super().__init__()
    
    def run(self): 
        self.stringAlg.createStringImage()
    
    def getProgress(self): 
        return self.stringAlg.progress
    
    def getLineSequence(self): 
        if int(self.getProgress()) == 1: 
            return self.stringAlg.line_sequence
        else: 
            return None


class StringAlg: 

    def __init__(self, numPins, maxLines, lineWeight, image):
        self.MIN_LOOP = 30 #prevent getting stuck in loop
        self.MIN_DIST = 20
        self.SCALE = 25
        self.HOOP_DIM = 0.625
        self.progress = 0

        self.NUM_PINS = int(numPins)
        self.MAX_LINES = int(maxLines)
        self.LINE_WEIGHT = int(lineWeight)

        self.img = readb64(image)[:, :, 0]
        self.length = self.img.shape[0]
        self.line_cache_y = [None] * self.NUM_PINS * self.NUM_PINS
        self.line_cache_x = [None] * self.NUM_PINS * self.NUM_PINS
        self.line_cache_weight = [1] * self.NUM_PINS * self.NUM_PINS
        self.line_cache_length = [0] * self.NUM_PINS * self.NUM_PINS

    def _circle_mask(self): 
        X,Y = np.ogrid[0:self.length, 0:self.length]
        circlemask = (X - self.length/2) ** 2 + (Y - self.length/2) ** 2 > self.length/2 * self.length/2
        self.img[circlemask] = 0xFF

    def _precalculate_lines(self, pin_coords): 

        center = self.length / 2
        radius = self.length / 2 - 1/2

        # Precalculate the coordinates of every pin
        for i in range(self.NUM_PINS):
            angle = 2 * math.pi * i / self.NUM_PINS
            pin_coords.append((math.floor(center + radius * math.cos(angle)),
                               math.floor(center + radius * math.sin(angle))))

        print("Precalculating all lines... ", end='', flush=True)

        for a in range(self.NUM_PINS):
            for b in range(a + self.MIN_DIST, self.NUM_PINS):
                x0 = pin_coords[a][0]
                y0 = pin_coords[a][1]

                x1 = pin_coords[b][0]
                y1 = pin_coords[b][1]

                d = int(math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0)*(y1 - y0)))

                #d = max(abs(y1-y0), abs(x1-x0)) inf-norm
                
                # A proper (slower) Bresenham does not give any better result *shrug*
                xs = np.linspace(x0, x1, d, dtype=int)
                ys = np.linspace(y0, y1, d, dtype=int)

                self.line_cache_y[b*self.NUM_PINS + a] = ys
                self.line_cache_y[a*self.NUM_PINS + b] = ys
                self.line_cache_x[b*self.NUM_PINS + a] = xs
                self.line_cache_x[a*self.NUM_PINS + b] = xs
                self.line_cache_length[b*self.NUM_PINS + a] = d
                self.line_cache_length[a*self.NUM_PINS + b] = d


        print("done")
    
    def _print_error(self, result, l): 
            if l % 100 == 0:
                print("%d " % l, end='', flush=True)
                # print(self.img.shape)
                img_result = cv2.resize(result, self.img.shape, interpolation=cv2.INTER_AREA)

                # Some trickery to fast calculate the absolute difference, to estimate the error per pixel
                diff = img_result - self.img
                mul = np.uint8(img_result < self.img) * 254 + 1
                absdiff = diff * mul
                print(absdiff.sum() / (self.length * self.length))
    
    def _get_best_pin(self, pin, last_pins, error): 
        max_err = -math.inf
        best_pin = -1

        # Find the line which will lower the error the most
        for offset in range(self.MIN_DIST, self.NUM_PINS - self.MIN_DIST):
            test_pin = (pin + offset) % self.NUM_PINS
            if test_pin in last_pins:
                continue

            xs = self.line_cache_x[test_pin * self.NUM_PINS + pin]
            ys = self.line_cache_y[test_pin * self.NUM_PINS + pin]

            # Simple
            # Error defined as the sum of the brightness of each pixel in the original
            # The idea being that a wire can only darken pixels in the result
            line_err = np.sum(error[ys,xs])

            if line_err > max_err:
                max_err = line_err
                best_pin = test_pin
        return best_pin
    
    def _update_error(self, error, best_pin, pin, line_mask):
            xs = self.line_cache_x[best_pin * self.NUM_PINS + pin]
            ys = self.line_cache_y[best_pin * self.NUM_PINS + pin]
            weight = self.LINE_WEIGHT

            # Subtract the line from the error
            line_mask.fill(0)
            line_mask[ys, xs] = weight
            error = error - line_mask
            error.clip(0, 255)
            return error
    
    def _update_string_dist(self, thread_length, pin_coords, pin, best_pin): 
            x0 = pin_coords[pin][0]
            y0 = pin_coords[pin][1]

            x1 = pin_coords[best_pin][0]
            y1 = pin_coords[best_pin][1]

            # Calculate physical distance
            dist = math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0)*(y1 - y0))
            thread_length += self.HOOP_DIM / self.length * dist


    def _calculate_lines(self, pin_coords): 
        error = np.ones(self.img.shape) * 0xFF - self.img.copy()

        img_result = np.ones(self.img.shape) * 0xFF

        result = np.ones((self.img.shape[0] * self.SCALE, self.img.shape[1] * self.SCALE), np.uint8) * 0xFF
        line_mask = np.zeros(self.img.shape, np.float64) # XXX

        self.line_sequence = []
        pin = 0
        self.line_sequence.append(pin)

        thread_length = 0

        last_pins = collections.deque(maxlen = self.MIN_LOOP)

        for l in range(self.MAX_LINES):

            self._print_error(result, l)
            best_pin = self._get_best_pin(pin, last_pins, error)
            self.line_sequence.append(best_pin)

            error = self._update_error(error, best_pin, pin, line_mask)

            # Draw the line in the result
            cv2.line(result,
                (pin_coords[pin][0] * self.SCALE,      pin_coords[pin][1] * self.SCALE),
                (pin_coords[best_pin][0] * self.SCALE, pin_coords[best_pin][1] * self.SCALE),
                color=0, thickness=4, lineType=8)
            
            self._update_string_dist(thread_length, pin_coords, pin, best_pin)

            last_pins.append(best_pin)
            pin = best_pin
            self.progress = l/(self.MAX_LINES - 1)

    def createStringImage(self): 
        pin_coords = []
        self._circle_mask()
        self._precalculate_lines(pin_coords)
        self._calculate_lines(pin_coords)
        


def readb64(uri):
    encoded_data = uri.split(',')[1]
    nparr = np.fromstring(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img



