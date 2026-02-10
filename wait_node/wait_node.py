import dtlpy as dl
import logging

logger = logging.getLogger(name='wait_node')


class ServiceRunner(dl.BaseServiceRunner):
    def __init__(self):
        self.cycle_status_dict = {}

    def get_previous_nodes(self, pipeline, start_node_id, previous_nodes):
        """
        Recursively collects previous nodes in the pipeline and stores them in previous_nodes.
        """
        for connection in pipeline.connections:
            connection: dl.PipelineConnection
            if connection.target.node_id == start_node_id:
                if connection.source.node_id not in previous_nodes:
                    previous_nodes[connection.source.node_id] = {}
                    self.get_previous_nodes(pipeline, connection.source.node_id, previous_nodes)

    @staticmethod
    def get_node_executions_status(node_id, pipeline_execution_id):
        """
        Get all executions that happened on the node from current cycle,
         if not all executions are in status success return False to stop pipeline.
        """
        filters = dl.Filters(resource=dl.FiltersResource.EXECUTION)
        filters.add(field='pipeline.executionId', values=pipeline_execution_id)
        filters.add(field='pipeline.nodeId', values=node_id)
        executions = dl.executions.list(filters=filters)
        for execution in executions.all():
            execution: dl.Execution
            # If any of the executions is NOT in success status, return False
            if execution.latest_status.get('status') != 'success':
                return False
        return True

    def wait_for_cycle(self, item: dl.Item, context: dl.Context, progress: dl.Progress):
        """
        Waits for the cycle to complete based on the status of previous nodes in the pipeline execution.
        """

        node_context = context.node
        return_parent = node_context.metadata.get('customNodeConfig', dict()).get('returnParent', False)
        if return_parent is True:
            parent_item_id = item.metadata.get('user', dict()).get('parentItemId', '')
            try:  # try to get parent item
                parent_item = item.dataset.items.get(item_id=parent_item_id)
            except dl.exceptions.NotFound:
                logging.error(f'Parent item not found: {parent_item_id}, returning item itself.')
                parent_item = item
        else:
            parent_item = item

        node_id = context.node_id
        pipeline_execution_id = context.pipeline_execution_id
        pipeline_id = context.pipeline_id
        cache_key = f"{pipeline_execution_id}_{node_id}"

        # If we already determined all previous nodes completed for this
        # pipeline execution + node, let subsequent items through immediately.
        cycle_status = self.cycle_status_dict.get(cache_key, 'wait')
        if cycle_status == 'continue':
            progress.update(action='continue')
            return parent_item

        # Fetch pipeline execution status
        success, response = dl.client_api.gen_request(
            req_type="get",
            path=f"/pipelines/{pipeline_id}/executions/{pipeline_execution_id}"
        )

        latest_status = 'wait'
        if success:
            nodes = response.json().get('nodes', list())
            previous_nodes = dict()
            pipeline = context.pipeline

            # Collect previous nodes
            self.get_previous_nodes(pipeline=pipeline, start_node_id=node_id, previous_nodes=previous_nodes)

            # Assume all done until proven otherwise
            all_done = True
            for node in nodes:
                if node.get('id', None) in list(previous_nodes.keys()):
                    if not self.get_node_executions_status(node_id=node.get('id'),
                                                          pipeline_execution_id=pipeline_execution_id):
                        all_done = False
                        break

            if all_done:
                latest_status = 'continue'

        # Cache the result so subsequent items skip the check once predecessors are done
        self.cycle_status_dict[cache_key] = latest_status
        progress.update(action=latest_status)
        return parent_item





if __name__ == '__main__':
    # Run Locally
    context = dl.Context()
    context.pipeline_id = ''
    context.node_id = ''
    context.pipeline_execution_id = ''
    _item = dl.items.get(item_id='')
    service_runner = ServiceRunner()
    service_runner.wait_for_cycle(item=_item, context=context, progress=dl.Progress())
