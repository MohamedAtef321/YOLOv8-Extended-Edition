# Ultralytics YOLO 🚀, AGPL-3.0 license

import torch
import numpy as np

from ultralytics.yolo.engine.predictor import BasePredictor
from ultralytics.yolo.engine.results import Results
from ultralytics.yolo.utils import DEFAULT_CFG, ROOT, ops
from ultralytics.yolo.utils.plotting import Annotator, colors, save_one_box

# importing our custom functions
from ultralytics.yolo.utils.night_vision import apply_night_vision, night_vision_core
from ultralytics.yolo.utils.lane_detection import lane_detection_core
from ultralytics.yolo.utils.spi import spi_send, spi_remap


class DetectionPredictor(BasePredictor):

    def get_annotator(self, img):
        return Annotator(img, line_width=self.args.line_thickness, example=str(self.model.names))

    def preprocess(self, img):
        img = (img if isinstance(img, torch.Tensor) else torch.from_numpy(img)).to(self.model.device)
        img = img.half() if self.model.fp16 else img.float()  # uint8 to fp16/32
        img /= 255  # 0 - 255 to 0.0 - 1.0

        # Night vision mode
        if self.args.night_vision:

            # check if source is a webcam
            img = torch.squeeze(img)
            img = apply_night_vision(img,
                                     image_gamma=self.args.image_gamma,
                                     min_gamma=self.args.min_gamma,
                                     max_gamma=self.args.max_gamma,
                                     min_normalized_intensity=self.args.min_normalized_intensity)

        return img

    def postprocess(self, preds, img, orig_imgs):
        """Postprocesses predictions and returns a list of Results objects."""
        preds = ops.non_max_suppression(preds,
                                        self.args.conf,
                                        self.args.iou,
                                        agnostic=self.args.agnostic_nms,
                                        max_det=self.args.max_det,
                                        classes=self.args.classes)

        results = []
        for i, pred in enumerate(preds):
            orig_img = orig_imgs[i] if isinstance(orig_imgs, list) else orig_imgs
            if not isinstance(orig_imgs, torch.Tensor):
                pred[:, :4] = ops.scale_boxes(img.shape[2:], pred[:, :4], orig_img.shape)
            path = self.batch[0]
            img_path = path[i] if isinstance(path, list) else path
            results.append(Results(orig_img=orig_img, path=img_path, names=self.model.names, boxes=pred))
        return results

    def write_results(self, idx, results, batch):
        p, im, im0 = batch
        log_string = ''
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim
        self.seen += 1
        imc = im0.copy() if self.args.save_crop else im0
        if self.source_type.webcam or self.source_type.from_img:  # batch_size >= 1
            log_string += f'{idx}: '
            frame = self.dataset.count
        else:
            frame = getattr(self.dataset, 'frame', 0)
        self.data_path = p
        self.txt_path = str(self.save_dir / 'labels' / p.stem) + ('' if self.dataset.mode == 'image' else f'_{frame}')
        log_string += '%gx%g ' % im.shape[2:]  # print string

        # apply Night Vision mode on original image
        if self.args.night_vision == 'show':
            im0 = night_vision_core(im0, self.args.image_gamma, self.args.min_gamma, self.args.max_gamma,
                                    self.args.min_normalized_intensity)

        # apply Lane Detection mode on original image
        if self.args.lane_detection:
            try :
                im0 = lane_detection_core(im0,
                                        CANNY_THRESHOLD_1= self.args.CANNY_THRESHOLD_1,
                                        CANNY_THRESHOLD_2= self.args.CANNY_THRESHOLD_2,
                                        MIN_VOTES= self.args.MIN_VOTES,
                                        MIN_LINE_LEN= self.args.MIN_LINE_LEN,
                                        MAX_LINE_GAP= self.args.MAX_LINE_GAP,
                                        line_color= self.args.lane_line_color,
                                        line_thickness= self.args.lane_line_thickness)
            except:
                print("Lane detection failed!")

        self.annotator = self.get_annotator(np.ascontiguousarray(im0))

        det = results[idx].boxes  # TODO: make boxes inherit from tensors
        if len(det) == 0:
            return f'{log_string}(no detections), '
        for c in det.cls.unique():
            n = (det.cls == c).sum()  # detections per class
            #print("c: ", int(c), ", n: ", int(n))
            #print("class: ", self.model.names[int(c)])

            # send class to SPI
            if self.args.spi:
                
                # remaping for Embedded requirements 
                spi_c = spi_remap(int(c))
                # print("c: ", int(c), ", spi_c: ", int(spi_c))

                # send class to SPI
                spi_send([int(spi_c)], 
                        spi_mode = self.args.spi_mode, 
                        spi_speed = self.args.spi_speed, 
                        spi_sleep = self.args.spi_sleep,
                        spi_device = self.args.spi_device,
                        spi_port = self.args.spi_port)


            log_string += f"{n} {self.model.names[int(c)]}{'s' * (n > 1)}, "

        # write
        for d in reversed(det):
            c, conf, id = int(d.cls), float(d.conf), None if d.id is None else int(d.id.item())
            if self.args.save_txt:  # Write to file
                line = (c, *d.xywhn.view(-1)) + (conf, ) * self.args.save_conf + (() if id is None else (id, ))
                with open(f'{self.txt_path}.txt', 'a') as f:
                    f.write(('%g ' * len(line)).rstrip() % line + '\n')
            if self.args.save or self.args.show:  # Add bbox to image
                name = ('' if id is None else f'id:{id} ') + self.model.names[c]
                label = (f'{name} {conf:.2f}' if self.args.show_conf else name) if self.args.show_labels else None
                self.annotator.box_label(d.xyxy.squeeze(), label, color=colors(c, True))
            if self.args.save_crop:
                save_one_box(d.xyxy,
                             imc,
                             file=self.save_dir / 'crops' / self.model.names[c] / f'{self.data_path.stem}.jpg',
                             BGR=True)

        return log_string


def predict(cfg=DEFAULT_CFG, use_python=False):
    """Runs YOLO model inference on input image(s)."""
    model = cfg.model or 'yolov8n.pt'
    source = cfg.source if cfg.source is not None else ROOT / 'assets' if (ROOT / 'assets').exists() \
        else 'https://ultralytics.com/images/bus.jpg'

    args = dict(model=model, source=source)
    if use_python:
        from ultralytics import YOLO
        YOLO(model)(**args)
    else:
        predictor = DetectionPredictor(overrides=args)
        predictor.predict_cli()


if __name__ == '__main__':
    predict()
