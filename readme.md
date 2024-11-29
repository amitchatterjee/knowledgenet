# One-time setup
This project needs python 3.9 or higher installed. It may work with other versions as well.  

Install the appropriate packages:
>> pip install -U pytest pytest-cov  
   pip install build
   pip install debugpy

# Run pytests:
>> cd engine  
   python -m pytest -rPX -vv --cov

# Build package:
>> cd engine  
   python -m build

