# City Safety Dashboard

This is an interactive dashboard which allows the user to visulaize the cleaned dataset with choopleth, time series grouped line chart and gar chart

### AI used:

ChatGPT was used for creating the dashboard and improving its functionality and style 

## How to run:

The app was built in VS Code however it also runs in Colab

**Run the app in Colab:**

1. Upload the incidents_17952.csv and zones_17952.geojson.txt files into Colab environment with:

```bash
from google.colab import files

uploaded = files.upload()
```

2. Install the streamlit pyngrok with:

```bash
!pip install streamlit pyngrok
!pip install pyngrok
```

3. Install the geopands plotly folium shapely with:

```bash
!pip install geopandas plotly folium shapely
```

4. Insert the app code right after this line:

```bash
%%writefile app.py
```
5. Run the app with:

```bash
from pyngrok import ngrok
!streamlit run app.py &
print(ngrok.connect(8501))
```

6. Open the local URL


## What worked and not

I did not manage to change the allocation of graphs for them to look like a real dashboard, however in my opinion it is still clearly visible and good looking

Also, I dis not add the export static dashboard feature, cause I did not understand the logic behind even when I tried mock test at home. Well, I managed to upload the dashboard but it was not in a good quality I wanted it to be.

Everything else I wanted to add - I managed.