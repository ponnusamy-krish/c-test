"""python src/preview.py out.png t1 t2 ...   (use RENDER_SCALE=0.25 PREVIEW_STANDIN=1)"""
import sys, time
import cv2, numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import frame
from engine import FPS
out, times = sys.argv[1], [float(a) for a in sys.argv[2:]]
tiles = []
for t in times:
    t0 = time.time(); f = frame.build_frame(int(round(t * FPS)))
    print(f"t={t:6.2f}s  {1000*(time.time()-t0):6.0f} ms")
    cv2.putText(f, f"{t:.2f}s", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    tiles.append(f)
cv2.imwrite(out, np.hstack(tiles))
