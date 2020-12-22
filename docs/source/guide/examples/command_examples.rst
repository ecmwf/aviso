.. _command_examples:

Command
=================

Below find an example of a basic event listener for ``dissemination`` events that will execute a ``command`` trigger 
in case of notifications. Note the parameter substitution mechanism for the command and the environment variables defined.

.. literalinclude:: command_listener.yaml
   :language: yaml

Below find a similar example of a ``command`` trigger. This time the parameter substitution is passing the entire
notification as json.

.. literalinclude:: command_json_listener.yaml
   :language: yaml

Below find a similar example of a ``command`` trigger. This time the parameter substitution is passing the file
path to a json file containing the notification.

.. literalinclude:: command_json_path_listener.yaml
   :language: yaml

Finally, find below the example shell script executed by the triggers above. Note how the parameters are passed 
from the triggers to the script.

.. literalinclude:: script.sh
   :language: sh
