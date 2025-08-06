[21:07:32] 📦 Processed dependencies!

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

[21:07:33] 🔄 Updated app!

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

[21:07:53] ❗️ 

2025-08-06 21:07:53.730 503 GET /script-health-check (127.0.0.1) 346.10ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:07:58.683 503 GET /script-health-check (127.0.0.1) 335.92ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:03.673 503 GET /script-health-check (127.0.0.1) 338.87ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:08.756 503 GET /script-health-check (127.0.0.1) 346.12ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:13.700 503 GET /script-health-check (127.0.0.1) 354.07ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:18.703 503 GET /script-health-check (127.0.0.1) 350.93ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:23.731 503 GET /script-health-check (127.0.0.1) 376.26ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:29.120 503 GET /script-health-check (127.0.0.1) 607.87ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:34.057 503 GET /script-health-check (127.0.0.1) 591.62ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:38.972 503 GET /script-health-check (127.0.0.1) 513.11ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:44.048 503 GET /script-health-check (127.0.0.1) 553.22ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:48.972 503 GET /script-health-check (127.0.0.1) 483.15ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:53.641 503 GET /script-health-check (127.0.0.1) 313.74ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:08:58.669 503 GET /script-health-check (127.0.0.1) 321.65ms

────────────────────── Traceback (most recent call last) ───────────────────────

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/exec_code.py:128 in exec_func_with_error_handling                        

                                                                                

  /home/adminuser/venv/lib/python3.13/site-packages/streamlit/runtime/scriptru  

  nner/script_runner.py:669 in code_to_exec                                     

                                                                                

  /mount/src/rfq-sender/app.py:8 in <module>                                    

                                                                                

      5 import os                                                               

      6 import json                                                             

      7 from utils.auth import load_users, get_user_role                        

  ❱   8 from utils.queue import load_queue, add_to_queue, QUEUE_PATH            

      9 import logging                                                          

     10 from core.config import Paths, ExchangeConfig, CompanyInfo, AppConfig,  

     11                                                                         

                                                                                

  /mount/src/rfq-sender/utils/queue.py:5 in <module>                            

                                                                                

      2 import os                                                               

      3 import logging                                                          

      4 from pathlib import Path                                                

  ❱   5 from core.config import Paths, LoggingConfig, init_config               

      6                                                                         

      7 # Initialize configuration                                              

      8 init_config()                                                           

                                                                                

  /mount/src/rfq-sender/core/config.py:24 in <module>                           

                                                                                

     21                                                                         

     22 # Get the project root directory                                        

     23 ROOT_DIR = os.environ.get("APP_ROOT_DIR", Path(__file__).parent.parent  

  ❱  24 logger.info(f"Using ROOT_DIR: {ROOT_DIR}")                              

     25                                                                         

     26 # Logging configuration                                                 

     27 class LoggingConfig:                                                    

────────────────────────────────────────────────────────────────────────────────

NameError: name 'logger' is not defined

2025-08-06 21:09:03.649 503 GET /script-health-check (127.0.0.1) 314.34ms

master
