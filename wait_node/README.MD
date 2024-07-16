# Wait Node

### Description

The `wait` custom node is a helpful tool that can be added to any location in the pipeline. It will wait for all previous executions to finish before continuing.

### Example Use cases:

* [Image Tiling](https://github.com/dataloop-ai-apps/image-tiling-nodes) - In this example, the `wait` node is used to ensure that all the work that needs to be done on the tiles is finished before the rest of the flow is activated.

* Working with Batches: The `wait` node can be used to ensure that all the items in a batch are processed before moving on to the next step.

### Configurations: 

* [Wait Node](wait_node/README.md) - A node that can be put in any location in the pipeline, and it will wait for all previous executions to finish before continuing.

## Contributions, Bugs and Issues - How to Contribute

We welcome anyone to help us improve this app.  
[Here's](CONTRIBUTING.md) a detailed instructions to help you open a bug or ask for a feature request.
