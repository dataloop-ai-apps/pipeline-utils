import logging
import threading
import time
import dtlpy as dl

logger = logging.getLogger(name='wait_node')

# Statuses that indicate the execution is done (no more updates expected)
FINAL_STATUSES = {'success', 'failed'}

# Polling: 4 seconds between polls, max 4 retries (5 attempts total)
POLL_INTERVAL_SEC = 4
POLL_MAX_RETRIES = 4


class ServiceRunner(dl.BaseServiceRunner):
    def __init__(self):
        self.cycle_status_dict = {}
        self._state_lock = threading.Lock()

    def get_previous_nodes(self, pipeline, start_node_id, previous_nodes):
        """
        Recursively collects previous nodes in the pipeline and stores them in previous_nodes.
        """
        for connection in pipeline.connections:
            connection: dl.PipelineConnection
            if connection.target.node_id in start_node_id:
                if connection.source.node_id not in previous_nodes:
                    previous_nodes[connection.source.node_id] = {}
                    self.get_previous_nodes(pipeline, connection.source.node_id, previous_nodes)

    @staticmethod
    def get_node_executions_status(node_id, pipeline_execution_id):
        """
        Get all executions that happened on the node from current cycle.
        Returns:
            (True, None): all executions in success (final).
            (False, execution): at least one execution failed (final).
            ('pending', execution): at least one execution has non-final status (e.g. in_progress).
        """
        filters = dl.Filters(resource=dl.FiltersResource.EXECUTION)
        filters.add(field='pipeline.executionId', values=pipeline_execution_id)
        filters.add(field='pipeline.nodeId', values=node_id)
        executions = dl.executions.list(filters=filters)
        for execution in executions.all():
            execution: dl.Execution
            status = execution.latest_status.get('status')
            if status not in FINAL_STATUSES:
                return 'pending', execution
            if status == 'failed':
                return False, execution
        return True, None

    def wait_for_cycle(self, item: dl.Item, context: dl.Context, progress: dl.Progress):
        """
        Waits for the cycle to complete based on the status of previous nodes in the pipeline execution.
        Polls until executions have final status (success/failed), 4s between polls, max 4 retries.
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

        latest_status = 'continue'
        node_id = context.node_id
        pipeline_execution_id = context.pipeline_execution_id
        pipeline_id = context.pipeline_id

        # Fetch pipeline execution status
        success, response = dl.client_api.gen_request(
            req_type="get",
            path=f"/pipelines/{pipeline_id}/executions/{pipeline_execution_id}"
        )

        # Get current cycle status (locked)
        with self._state_lock:
            cycle_status = self.cycle_status_dict.get(f"{pipeline_execution_id}_{node_id}", 'wait')

        if success and not cycle_status == 'continue':
            nodes = response.json().get('nodes', list())
            previous_nodes = dict()
            pipeline = context.pipeline

            # Collect previous nodes
            self.get_previous_nodes(pipeline=pipeline, start_node_id=node_id, previous_nodes=previous_nodes)

            for node in nodes:
                if node.get('id', None) not in list(previous_nodes.keys()):
                    continue
                node_id_to_check = node.get('id')
                result, execution = None, None
                for attempt in range(POLL_MAX_RETRIES + 1):
                    result, execution = self.get_node_executions_status(
                        node_id=node_id_to_check,
                        pipeline_execution_id=pipeline_execution_id
                    )
                    if result != 'pending':
                        break
                    if attempt < POLL_MAX_RETRIES:
                        logger.info(
                            f"Node {node_id_to_check} has non-final execution status, "
                            f"polling in {POLL_INTERVAL_SEC}s (attempt {attempt + 1}/{POLL_MAX_RETRIES + 1})"
                        )
                        time.sleep(POLL_INTERVAL_SEC)
                if result is True:
                    logger.info(f"Node {node_id_to_check} has all executions in success status, Checking next node...")
                    continue
                elif result == 'pending':
                    latest_status = 'wait'
                    logger.info(
                        f"Node {node_id_to_check} still has non-final execution status after {POLL_MAX_RETRIES + 1} attempts, Stopping pipeline..."
                    )
                    break
                else:
                    latest_status = 'wait'
                    if execution is not None:
                        logger.info(f"Node {node_id_to_check} has failed execution: {execution.id}, Stopping pipeline...")
                        logger.info(f"Execution details: {execution.to_json()}, execution Output: {execution.output}")
                    else:
                        logger.info(f"Node {node_id_to_check} has executions in not success status, Stopping pipeline...")
                    break
            else:
                latest_status = 'continue'

            with self._state_lock:
                self.cycle_status_dict[f"{pipeline_execution_id}_{node_id}"] = latest_status
            logger.info(f'Latest status set to: {latest_status}, cycle status for {pipeline_execution_id}_{node_id}: {cycle_status}')
        else:
            latest_status = 'wait'
            logger.info(f'Latest set to status: {latest_status}, cycle status for {pipeline_execution_id}_{node_id}: {cycle_status}')

        progress.update(action=latest_status)
        logger.info(f'Progress updated to: {latest_status}')
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
