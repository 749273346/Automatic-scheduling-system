from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Size settings
    size = (256, 256)
    
    # Colors
    bg_color = (41, 128, 185)  # Professional Blue
    white = (255, 255, 255)
    dark_blue = (21, 67, 96)
    
    # Create image with transparent background
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw rounded rectangle background
    # Since PIL doesn't have a direct rounded rectangle with nice anti-aliasing in older versions, 
    # we can draw a rectangle and circles or just a standard rectangle for simplicity or use a large circle.
    # Let's try a rounded rectangle manually.
    
    margin = 20
    radius = 40
    
    # Main body rects
    draw.rectangle([margin + radius, margin, size[0] - margin - radius, size[1] - margin], fill=bg_color)
    draw.rectangle([margin, margin + radius, size[0] - margin, size[1] - margin - radius], fill=bg_color)
    
    # Corners
    draw.pieslice([margin, margin, margin + 2*radius, margin + 2*radius], 180, 270, fill=bg_color)
    draw.pieslice([size[0] - margin - 2*radius, margin, size[0] - margin, margin + 2*radius], 270, 360, fill=bg_color)
    draw.pieslice([margin, size[1] - margin - 2*radius, margin + 2*radius, size[1] - margin], 90, 180, fill=bg_color)
    draw.pieslice([size[0] - margin - 2*radius, size[1] - margin - 2*radius, size[0] - margin, size[1] - margin], 0, 90, fill=bg_color)
    
    # Draw Calendar Top Header
    header_height = 70
    # Rounded top part for header (darker blue)
    # We redraw the top part with darker color
    # Top Left Corner
    draw.pieslice([margin, margin, margin + 2*radius, margin + 2*radius], 180, 270, fill=dark_blue)
    # Top Right Corner
    draw.pieslice([size[0] - margin - 2*radius, margin, size[0] - margin, margin + 2*radius], 270, 360, fill=dark_blue)
    # Top Center Rect
    draw.rectangle([margin + radius, margin, size[0] - margin - radius, margin + radius], fill=dark_blue)
    # Header Body Rect
    draw.rectangle([margin, margin + radius, size[0] - margin, margin + header_height], fill=dark_blue)

    # Draw "S" for Scheduler or Smart
    # Or draw a simple grid to represent calendar
    
    # Grid settings
    grid_margin_x = 50
    grid_margin_y = margin + header_height + 20
    cell_width = (size[0] - 2 * grid_margin_x) / 3
    cell_height = (size[1] - grid_margin_y - 40) / 3
    
    line_width = 6
    
    # Draw vertical lines
    x1 = grid_margin_x + cell_width
    x2 = grid_margin_x + 2 * cell_width
    y_start = grid_margin_y
    y_end = size[1] - 40
    
    draw.line([x1, y_start, x1, y_end], fill=white, width=line_width)
    draw.line([x2, y_start, x2, y_end], fill=white, width=line_width)
    
    # Draw horizontal lines
    y1 = grid_margin_y + cell_height
    y2 = grid_margin_y + 2 * cell_height
    x_start = grid_margin_x
    x_end = size[0] - grid_margin_x
    
    draw.line([x_start, y1, x_end, y1], fill=white, width=line_width)
    draw.line([x_start, y2, x_end, y2], fill=white, width=line_width)
    
    # Add a checkmark in the center cell
    # Center cell coords: x1 to x2, y1 to y2
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    
    # Checkmark points
    points = [
        (cx - 20, cy),
        (cx - 5, cy + 15),
        (cx + 25, cy - 25)
    ]
    draw.line(points, fill=white, width=10, joint='curve')
    
    # Save files
    if not os.path.exists('resources'):
        os.makedirs('resources')
        
    icon_path_png = os.path.join('resources', 'icon.png')
    icon_path_ico = os.path.join('resources', 'icon.ico')
    
    img.save(icon_path_png)
    # Save as ICO with multiple sizes
    img.save(icon_path_ico, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    
    print(f"Icons generated: {icon_path_png}, {icon_path_ico}")

if __name__ == "__main__":
    create_icon()
