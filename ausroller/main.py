from ausroller import Configuration
from ausroller import Ausroller

import logging

ROLLINGPIN = """
          _______________________
   _____ /|                     |\ _____
  (_____| |                     | |_____)
         \|_____________________|/
            A
              U
                S
                  R
                    O
                      L
                        L
                          E
                            R

"""

def main():
    print(ROLLINGPIN)
    # parse arguments from command line and
    # read configuration file

    c = Configuration()
    c.parse_args()
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=c.log_level)
    # repair gbp logging
    gbplogger = logging.getLogger("gbp")
    gbplogger.propagate = False
    c.read_config()

    a = Ausroller(c)
    a.deploy()

if __name__ == '__main__':
    main()
