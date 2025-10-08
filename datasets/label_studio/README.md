# Label Studio Conventions

This document outlines the conventions for using Label Studio for image annotation.

## Project Setup

- **Project Naming:** Projects should be named according to the model they are intended to train. For example, a project for labeling the exterior color of BMW M5 cars would be named `bmw_m5_exterior_color`.
- **Ontology:** The labeling ontology (the set of labels) for each project should be defined in a JSON file and stored in the repository under `datasets/label_studio/<project_name>/ontology.json`. This allows us to version control the labels.

## Initial Focus: Exterior Color

Our initial labeling efforts will be focused on identifying the exterior color of cars.

- **Labeling Task:** For each image, annotators should draw a bounding box around the car and select the appropriate color label.
- **Color Palette:** The initial color palette will be simple, focusing on common car colors. We can expand this over time.
  - Black
  - White
  - Silver
  - Gray
  - Blue
  - Red
  - Green
  - Brown
  - Other
- **Weak Labels:** Images imported into Label Studio will have "weak labels" pre-populated from the ad data (`make`, `model`, `year`, `color`, `official_color`). These can be used to help filter and sort images, but annotators should always rely on their own judgment when applying the final label.

## Data Flow

1.  **Import:** New images are added to the `images` table with a status of `raw`. A script will import these images into the appropriate Label Studio project.
2.  **Annotate:** Human annotators label the images in Label Studio.
3.  **Export:** Labeled data is exported from Label Studio.
4.  **Update:** A script processes the exported data and updates the `annotations` and `status` fields in the `images` table. The status will be updated to `labeled`.
