import cv2
import numpy as np
import onnxruntime


class ONNXBox:
    def __init__(self, xyxy):
        self.xyxy = [xyxy]


class ONNXResult:
    def __init__(self, boxes):
        self.boxes = boxes


class YOLOONNX:
    def __init__(self, model_path):
        opts = onnxruntime.SessionOptions()
        opts.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(model_path, sess_options=opts)
        self.input_name = self.session.get_inputs()[0].name

    def letterbox(self, im, new_shape=(640, 640), color=(114, 114, 114)):
        shape = im.shape[:2]
        if isinstance(new_shape, int):
            new_shape = (new_shape, new_shape)

        ratio = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
        new_unpad = int(round(shape[1] * ratio)), int(round(shape[0] * ratio))
        dw = new_shape[1] - new_unpad[0]
        dh = new_shape[0] - new_unpad[1]
        dw /= 2
        dh /= 2

        if shape[::-1] != new_unpad:
            im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)

        top = int(round(dh - 0.1))
        bottom = int(round(dh + 0.1))
        left = int(round(dw - 0.1))
        right = int(round(dw + 0.1))

        im = cv2.copyMakeBorder(
            im,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=color,
        )
        return im, (ratio, ratio), (dw, dh)

    def predict(self, source, conf=0.25, iou=0.45, verbose=False):
        if isinstance(source, str):
            img = cv2.imread(source)
            if img is None:
                raise ValueError(f"Could not read image from path: {source}")
        else:
            img = source.copy()

        original_height, original_width = img.shape[:2]
        input_size = 640
        letterboxed, ratio, (dw, dh) = self.letterbox(img, (input_size, input_size))

        img_rgb = cv2.cvtColor(letterboxed, cv2.COLOR_BGR2RGB)
        img_normalized = img_rgb.astype(np.float32) / 255.0
        img_transposed = np.transpose(img_normalized, (2, 0, 1))
        input_data = np.expand_dims(img_transposed, axis=0)

        outputs = self.session.run(None, {self.input_name: input_data})
        output = outputs[0][0].T

        boxes = []
        confidences = []

        for row in output:
            confidence = row[4]
            if confidence < conf:
                continue

            xc, yc, width, height = row[:4]
            x1 = xc - width / 2
            y1 = yc - height / 2

            x1_scaled = (x1 - dw) / ratio[0]
            y1_scaled = (y1 - dh) / ratio[1]
            width_scaled = width / ratio[0]
            height_scaled = height / ratio[1]

            boxes.append(
                [
                    int(x1_scaled),
                    int(y1_scaled),
                    int(width_scaled),
                    int(height_scaled),
                ]
            )
            confidences.append(float(confidence))

        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf, iou)
        onnx_boxes = []

        if len(indices) > 0:
            for idx in np.array(indices).flatten():
                x, y, width, height = boxes[idx]
                x1 = max(0, x)
                y1 = max(0, y)
                x2 = min(original_width, x + width)
                y2 = min(original_height, y + height)
                onnx_boxes.append(ONNXBox([x1, y1, x2, y2]))

        return [ONNXResult(onnx_boxes)]
