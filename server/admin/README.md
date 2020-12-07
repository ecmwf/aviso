# Aviso Admin

This component performs mainteinance operations to Aviso server in order to keep the store at constant size.
Currently the implementation regards only a etcd store. This store requires the following operations:
- Compaction, this operation removes the history older than a certain date
- Deletion, this operation deletes all the keys older than a certain date