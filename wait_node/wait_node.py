import dtlpy as dl
import logging

logger = logging.getLogger(name='wait_node')


class ServiceRunner(dl.BaseServiceRunner):
    def __init__(self):
        super().__init__()
        self.cycle_status_dict = {}

    @staticmethod
    def get_previous_nodes(pipeline, start_node_id, previous_nodes):
        """
        Recursively collects previous nodes in the pipeline and stores them in previous_nodes.
        """
        for connection in pipeline.connections:
            connection: dl.PipelineConnection
            if connection.target.node_id in start_node_id:
                if connection.source.node_id not in previous_nodes:
                    previous_nodes[connection.source.node_id] = {}
                    ServiceRunner.get_previous_nodes(pipeline, connection.source.node_id, previous_nodes)

    def wait_for_cycle(self, item: dl.Item, context: dl.Context, progress: dl.Progress):
        """
        Waits for the cycle to complete based on the status of previous nodes in the pipeline execution.
        """
        latest_status = 'continue'
        node_id = context.node_id
        pipeline_execution_id = context.pipeline_execution_id
        pipeline_id = context.pipeline_id

        # Fetch pipeline execution status
        success, response = dl.client_api.gen_request(
            req_type="get",
            path=f"/pipelines/{pipeline_id}/executions/{pipeline_execution_id}"
        )

        # Get current cycle status
        cycle_status = self.cycle_status_dict.get(pipeline_execution_id, 'wait')

        if success and not cycle_status == 'continue':
            nodes = response.json().get('nodes', list())
            previous_nodes = dict()
            pipeline = context.pipeline

            # Collect previous nodes
            self.get_previous_nodes(pipeline=pipeline, start_node_id=node_id, previous_nodes=previous_nodes)

            for node in nodes:
                if node.get('id', None) in list(previous_nodes.keys()):
                    if node.get('status') == 'success':
                        continue
                    else:
                        latest_status = 'wait'
                        break

            self.cycle_status_dict[pipeline_execution_id] = latest_status
        else:
            latest_status = 'wait'

        progress.update(action=latest_status)
        return item
