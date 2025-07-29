from tasks.scheduler import TaskScheduler

class TrafficGenerator:
    """
    A generator of network traffic
    """
    def __init__(self):
        self.scheduler = TaskScheduler()

    def http_request(self, host, url='www.google.com', duration=20):
        # TODO: Support for IP instead of URL
        if not url.startswith('www.'):
            url = 'www.' + url
        curl_func = lambda host, url : host.cmd(f"curl -s -o /dev/null https://{url}")
        self.scheduler.start_task(
            task_name='http_request',
            target_function=curl_func,
            duration=duration,
            args=(host, url)
        )

    def ftp_request(self, host, url, filename, duration=20):
        curl_func = lambda host, url, filename : host.cmd(f"curl -s -o /dev/null https://{url}/{filename}")
        self.scheduler.start_task(
            task_name='ftp_request',
            target_function=curl_func,
            duration=duration,
            args=(host, url, filename)
        )

    def wait_for_completion(self):
        self.scheduler.join_tasks()

    def stop(self):
        self.scheduler.stop_tasks()
