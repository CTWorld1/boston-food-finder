# Person B Prototype Results

Model: `gemini-3.6-flash`

| Input | Expected behavior | Actual result | Valid JSON? | Every populated field justified? | Pass? | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| no pizza | excluded contains "pizza" | {"budget_max":null,"craving":null,"cuisine":null,"dietary":[],"distance_miles":null,"excluded":["pizza"],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
| something crunchy | texture is "crunchy" | {"budget_max":null,"craving":null,"cuisine":null,"dietary":[],"distance_miles":null,"excluded":[],"open_now":null,"price_levels":[],"texture":"crunchy"} | Yes | Yes | Yes | OK |
| no seafood, no dairy, and nothing too spicy | all restrictions are captured correctly | {"budget_max":null,"craving":null,"cuisine":null,"dietary":[],"distance_miles":null,"excluded":["seafood","dairy","too spicy"],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
| Thai food within 2 miles | cuisine and distance are extracted | {"budget_max":null,"craving":null,"cuisine":"Thai","dietary":[],"distance_miles":2,"excluded":[],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
| Mexican under $20 | cuisine and budget are extracted | {"budget_max":20,"craving":null,"cuisine":"Mexican","dietary":[],"distance_miles":null,"excluded":[],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
| whatever is good | the model does not invent filters | {"budget_max":null,"craving":null,"cuisine":null,"dietary":[],"distance_miles":null,"excluded":[],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
| surprise me | the model returns mostly empty filters | {"budget_max":null,"craving":null,"cuisine":null,"dietary":[],"distance_miles":null,"excluded":[],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
| I want Japanese food, not raw fish, something light and crunchy | it captures cuisine, exclusions, and preferences | {"budget_max":null,"craving":"light","cuisine":"Japanese","dietary":[],"distance_miles":null,"excluded":["raw fish"],"open_now":null,"price_levels":[],"texture":"crunchy"} | Yes | Yes | Yes | OK |
| I want sushi but no seafood | it preserves both inputs without fixing the request | {"budget_max":null,"craving":null,"cuisine":"sushi","dietary":[],"distance_miles":null,"excluded":["seafood"],"open_now":null,"price_levels":[],"texture":null} | Yes | Yes | Yes | OK |
