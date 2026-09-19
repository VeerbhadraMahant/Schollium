# prompts/

One file per model step, named `<tool>.<step>.v<N>.txt`, for example `find.expand.v1.txt`. Code loads a prompt by name and version; the version in use is recorded in every run's config snapshot. To change a prompt, create the next version file. Never edit a version in place.
