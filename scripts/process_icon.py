import numpy as np
from PIL import Image, ImageDraw, ImageFilter

img = Image.open("build/Gemini_Generated_Image_z5k9hez5k9hez5k9.png").convert("RGBA")
arr = np.array(img)

# Very aggressive: find where meaningful (colorful) content is
# Exclude pure black (0,0,0) or very dark
is_dark = (arr[:, :, 0] < 20) & (arr[:, :, 1] < 20) & (arr[:, :, 2] < 20)
is_bright = (arr[:, :, 0] > 40) | (arr[:, :, 1] > 40) | (arr[:, :, 2] > 40)

content = is_bright & ~is_dark

rows = np.any(content, axis=1)
cols = np.any(content, axis=0)

row_idx = np.where(rows)[0]
col_idx = np.where(cols)[0]

if len(row_idx) > 20:
    y1, y2 = row_idx[0], row_idx[-1]
    x1, x2 = col_idx[0], col_idx[-1]

    # Add generous margin to keep glowing elements
    margin = 50
    cropped = img.crop(
        (
            max(0, x1 - margin),
            max(0, y1 - margin),
            min(1024, x2 + margin + 1),
            min(1024, y2 + margin + 1),
        ),
    )

    w, h = cropped.size
    print(f"Cropped to {w}x{h}")

    # Make square
    size = max(w, h)
    sq = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sq.paste(cropped, ((size - w) // 2, (size - h) // 2), cropped)

    # Create final with dark frame
    frame = 70
    final_w = size + frame * 2
    final = Image.new("RGBA", (final_w, final_w), (10, 10, 18, 255))

    # Paste content
    final.paste(sq, (frame, frame), sq)

    # Draw thin cyan border
    draw = ImageDraw.Draw(final)
    b = frame

    # Glow layers
    for i in range(3, 0, -1):
        alpha_val = int(100 * (i / 3))
        draw.rectangle(
            [b - i, b - i, final_w - b + i, final_w - b + i],
            outline=(20, 180, 255, alpha_val),
            width=1,
        )

    # Main thin border
    draw.rectangle([b, b, final_w - b, final_w - b], outline=(100, 220, 255, 200), width=2)

    # Smooth
    final = final.filter(ImageFilter.GaussianBlur(0.4))
    final = final.resize((1024, 1024), Image.Resampling.LANCZOS)

    final.save("build/icon_processed.png")
    print("✅ Icon processed! (1024x1024 with border)")
else:
    print("❌ Failed")
