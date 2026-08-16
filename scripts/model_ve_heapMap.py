from anomalib.data import Folder
from anomalib.models import Patchcore
from anomalib.engine import Engine

# Folder datamodule — kendi verilerimiz
datamodule = Folder(
    name="waypoint_dataset",
    root="D:/STAJ/akilli_fabrika_staj-2026/data/waypoints",
    normal_dir="normal",
    abnormal_dir="abnormal",
    train_batch_size=4,
    eval_batch_size=4,
)

model = Patchcore(
    backbone="resnet18",        # az veriyle iyi çalışır
    coreset_sampling_ratio=0.1,
)

if __name__ == '__main__':
    engine = Engine(max_epochs=1)
    engine.fit(datamodule=datamodule, model=model)
    predictions = engine.predict(datamodule=datamodule, model=model)
