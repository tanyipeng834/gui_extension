from GUI import GUI


input_path = 'data/input/screenshot_400.png'
output_root = 'data/output'

gui = GUI(img_file=input_path, output_dir=output_root)
gui.detect_element(True, True, True)
gui.load_detection_result()
gui.visualize_element_detection()
gui.recognize_layout()
gui.visualize_layout_recognition()
gui.convert_to_label_format()
