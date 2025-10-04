
#!/bin/bash
# Usage: ./image.sh image1 image2 ...
image_names=("$@")

# Build the images
for image_name in "${image_names[@]}"; do
    cd $image_name
    image_path=$LOCATION-docker.pkg.dev/$PROJECT_ID/cake-fair/$image_name/$STAGE
    echo "Building $image_path..."
    # pull the latest image to use as a cache, if it exists
    docker pull "$image_path:latest" || true
    docker build -t "$image_path:latest" -t "$image_path:$SHORT_SHA" --cache-from "$image_path:latest" --network=cloudbuild .
    echo "Pushing $image_name..."
    docker push --all-tags "$image_path"
    cd ..
    echo "Done $image_name"
done
