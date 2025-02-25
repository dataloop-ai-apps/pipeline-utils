import pandas as pd
import dtlpy as dl
import tempfile
import logging
import json
import os

logger = logging.getLogger(name="csv_to_json")


class ServiceRunner(dl.BaseServiceRunner):

    @staticmethod
    def csv_to_json(item: dl.Item):
        logger.info(f"Starting CSV to JSON conversion for item id: {item.id}")

        if not item.mimetype == "text/csv":
            raise ValueError(f"Item id : {item.id} is not a csv file! This functions excepts csv only")

        item_name = os.path.splitext(item.name)[0]
        # Download item
        with tempfile.TemporaryDirectory() as temp_dir:
            logger.info(f"Downloading item to temporary directory: {temp_dir}")
            item_local_path = item.download(local_path=temp_dir)
            logger.info(f"Item downloaded to: {item_local_path}")
            dir_path = os.path.join(temp_dir, item.id)
            os.makedirs(dir_path, exist_ok=True)
            with open(item_local_path, "r", encoding="utf-8") as csv_file:
                df = pd.read_csv(csv_file)
                for idx, row in df.iterrows():
                    new_json_file = os.path.join(dir_path, f"{item_name}_{idx}.json")
                    with open(new_json_file, "w", encoding="utf-8") as json_file:
                        json.dump(row.to_dict(), json_file, indent=4, ensure_ascii=False)

            logger.info("Uploading JSON files to dataset")
            uploaded_items = item.dataset.items.upload(
                local_path=os.path.join(dir_path, "*"),
                remote_path=f"{item.dir}",
                item_metadata={"user": {"originalItemId": item.id}},
                overwrite=True,
                return_as_list=True,
                raise_on_error=True
            )
        return uploaded_items
    
    def extract_dataset(self, dataset: dl.Dataset):
        logger.info(f"Extracting dataset: {dataset.name}")
        filters = dl.Filters()
        filters.add(field="metadata.system.mimetype", values="text/csv")
        for item in dataset.items.list(filters=filters):
            self.csv_to_json(item=item)


if __name__ == "__main__":
    # Run Locally
    dl.setenv("")
    test_item = dl.items.get(item_id="")
    service_runner = ServiceRunner()
    service_runner.csv_to_json(item=test_item)
