from scripts.box.box_integration import BoxIntegration
import pandas as pd
from io import BytesIO

box = BoxIntegration()
client = box.client
file = client.file('1980678657061')
content = file.content()  # bytes
# If this line raises, the exception is the clue

df = pd.read_csv(BytesIO(content))
print(df.head())
print(df.columns)