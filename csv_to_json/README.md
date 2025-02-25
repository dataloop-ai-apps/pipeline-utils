# CSV to JSON

### Description

The CSV to JSON application is designed to convert CSV files into JSON format, making it easier to integrate CSV data into JSON-based systems. Each column-row pair will be converted into a separate JSON file.

### Usage
Install the `csv_to_json` app from Marketplace. You can use it as:

1. As a pipeline node - `csv_to_json`.

2. As a trigger - This app includes a trigger for when a CSV item is uploaded to a dataset in the project, the trigger will convert the CSV to JSON and upload the JSON files to the same dataset in the `item.name/json` directory.


### Contributions, Bugs and Issues

We welcome contributions to improve this application. Please refer to the [contribution guidelines](../CONTRIBUTING.md) for more details. 