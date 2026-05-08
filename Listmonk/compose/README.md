use this docker run command to setup fresh database:

docker run -it \
  -v ./config.toml:/listmonk/config.toml \
  listmonk/listmonk:latest \
  ./listmonk --install
