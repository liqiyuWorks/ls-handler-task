from obs import ObsClient
import logging
import os




class ObsStore(object):
    def __init__(self, config):
        self.config = config
        # 华为云存储
        self.obs_client = ObsClient(
            access_key_id=config['obs_ak'],
            secret_access_key=config['obs_sk'],
            server=config['obs_server']
        )
        self.obs_bucket = config['obs_bucket']
        self.obs_domain = config['obs_domain']
        self.obs_root = config['obs_root']

    def set(self, data):
        file_name = data['file_name']
        obs_key = '{}/{}'.format(self.obs_root, data['obs_key'])
        obs_res = self.obs_client.putFile(self.obs_bucket, obs_key, file_name)
        if obs_res.status != 200:
            logging.error(
                'upload {} failed, res {}'.format(file_name, obs_res))
            return None
        # logging.info(obs_res.body.objectUrl)
        return '{}/{}'.format(self.obs_domain, obs_key)
