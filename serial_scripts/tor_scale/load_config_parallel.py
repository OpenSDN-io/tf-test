import multiprocessing as mp
from serial_scripts.tor_scale.load_config import ConfigScaleSetup


class ParallelScaleSetup(object):

    def __init__(self):

        config = ConfigScaleSetup()
        config.create_config_dict()

        # Define an output queue
        #output = mp.Queue()

        # Setup a list of processes that we want to run
        processes = [
            mp.Process(
                target=config.config_one_tor,
                args=(
                    config.tor_scale_dict,
                    tor)) for tor in list(config.tor_scale_dict.keys())]

        # Run processes
        for p in processes:
            p.start()

        # Exit the completed processes
        for p in processes:
            p.join()


if __name__ == "__main__":
    config = ParallelScaleSetup()
