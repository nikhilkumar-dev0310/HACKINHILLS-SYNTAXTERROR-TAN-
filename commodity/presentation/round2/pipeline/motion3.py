"""Where the page is changing (a slider moving, a number rolling, bars growing, the cursor), per source frame.
The spotlight in compose3.py follows this box. Writes motion3.json: [x, y, w, h] in page px, or null."""
import json, os
import cv2, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, "timeline3.json"))); VW, VH, NS = TL["vw"], TL["vh"], TL["frames"]
S = 12                                                      # analysis grid: 1/12 of the captured frame
prev, heat, out, box = None, None, [], None
for f in range(NS):
    im = cv2.imread(os.path.join(HERE, "frames3", f"{f:05d}.jpg"), cv2.IMREAD_GRAYSCALE)
    sm = cv2.resize(im, (im.shape[1] // S, im.shape[0] // S), interpolation=cv2.INTER_AREA).astype(np.float32)
    if prev is None: heat = np.zeros_like(sm)
    else: heat = heat * 0.86 + (np.abs(sm - prev) > 10)
    prev = sm
    m = heat > 2.3                                          # changing again and again in place (not a cursor passing)
    ys, xs = np.nonzero(m)
    k = sm.shape[1] / VW                                    # page px -> grid
    if 6 <= len(xs) and m.mean() < 0.22:                    # a compact change, not a scroll or a cut
        b = np.array([xs.min(), ys.min(), xs.max() + 1, ys.max() + 1], float) / k
        box = b if box is None or np.abs(b - box).max() > 120 else box * 0.8 + b * 0.2
        out.append([round(box[0]), round(box[1]), round(box[2] - box[0]), round(box[3] - box[1])])
    else:
        box = None if m.mean() >= 0.22 or len(xs) < 3 else box
        out.append(None if box is None else [round(box[0]), round(box[1]), round(box[2] - box[0]), round(box[3] - box[1])])
json.dump(out, open(os.path.join(HERE, "motion3.json"), "w"))
print("frames with a spotlight target:", sum(o is not None for o in out), "of", NS)
