import dtlpy as dl
import logging

logger = logging.getLogger(name='wait_node')


class ServiceRunner(dl.BaseServiceRunner):
    def __init__(self):
        self.cycle_status_dict = {}

    def wait_for_cycle(self, item: dl.Item, context: dl.Context, progress: dl.Progress):
        node = context.node
        return_parent = node.metdata['customNodeConfig']['returnParent']
        if return_parent:
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
        success, response = dl.client_api.gen_request(
            req_type="get",
            path="/pipelines/{pipeline_id}/executions/{pipeline_execution_id}".format(
                pipeline_id=context.pipeline_id,
                pipeline_execution_id=context.pipeline_execution_id))

        cycle_status = self.cycle_status_dict.get(context.pipeline_execution_id, 'wait')
        if success and not cycle_status == 'continue':
            nodes = response.json().get('nodes', list())
            for node in nodes:
                if (node.get('id', None) == node_id or node.get('status', None) == 'success' or node.get('status', None)
                        == 'pending'):
                    continue
                else:
                    latest_status = 'wait'
                    break
            self.cycle_status_dict[context.pipeline_execution_id] = latest_status
        else:
            latest_status = 'wait'

        progress.update(action=latest_status)

        return parent_item
