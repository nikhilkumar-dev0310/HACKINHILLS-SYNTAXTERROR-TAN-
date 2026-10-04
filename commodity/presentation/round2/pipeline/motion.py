import cv2, numpy as np, json, os
from concurrent.futures import ThreadPoolExecutor
N = json.load(open("timeline.json"))["frames"]
def g(f): return cv2.imread(f"frames/{f:05d}.jpg", cv2.IMREAD_REDUCED_GRAYSCALE_8).astype(np.int16)
with ThreadPoolExecutor(16) as ex: imgs = list(ex.map(g, range(N)))
d = [0.0] + [float(np.mean(np.abs(imgs[i] - imgs[i-1]) > 6)) for i in range(1, N)]
json.dump(d, open("motion.json", "w")); a = np.array(d)
print("frames", N, "moving(>0.2%)", int((a > .002).sum()), "p50 %.4f p90 %.4f" % (np.median(a), np.percentile(a, 90)))
