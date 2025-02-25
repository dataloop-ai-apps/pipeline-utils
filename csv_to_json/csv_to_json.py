import dtlpy as dl
import tempfile
import logging
import json
import csv
import os

logger = logging.getLogger(name="csv_to_json")


class ServiceRunner(dl.BaseServiceRunner):

    @staticmethod
    def csv_to_json(item: dl.Item):

        if not item.mimetype == "text/csv":
            raise ValueError(f"Item id : {item.id} is not a csv file! This functions excepts csv only")

        jsons_path_list = []
        item_name = os.path.splitext(item.name)[0]
        # Download item
        with tempfile.TemporaryDirectory() as temp_dir:
            item_local_path = item.download(local_path=temp_dir)
            with open(item_local_path, "r", encoding="utf-8") as csv_file:
                csv_reader = csv.DictReader(csv_file)
                for idx, row in enumerate(csv_reader):
                    print(row)
                    new_json_file = os.path.join(temp_dir, f"{item_name}_{idx}.json")
                    with open(new_json_file, "w", encoding="utf-8") as json_file:
                        json.dump(row, json_file, indent=4, ensure_ascii=False)
                    jsons_path_list.append(new_json_file)

            uploaded_items = item.dataset.items.upload(
                local_path=jsons_path_list,
                remote_path=f"jsons/{item_name}",
                item_metadata={"user": {"original_item_id": item.id}},
                overwrite=True,
            )

        if uploaded_items is None:
            raise dl.PlatformException("No items was uploaded!")
        elif isinstance(uploaded_items, dl.Item):
            uploaded_items = [uploaded_items]
        else:
            uploaded_items = [uploaded_item for uploaded_item in uploaded_items]

        return uploaded_items


if __name__ == "__main__":
    # Run Locally
    dl.setenv("")
    test_item = dl.items.get(item_id="")
    service_runner = ServiceRunner()
    service_runner.csv_to_json(item=test_item)
