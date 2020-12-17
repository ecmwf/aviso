.. _running_service:

Running as a service
=====================

Aviso can be executed as a system service. This helps automating its restart in case of machine reboots. 
The following steps help to configure Aviso to run as a service that automatically restarts:

1. Identify the location of Aviso executable:

   .. code-block:: console
      
      % whereis aviso

2. Create a system service unit, by creating the following file in `/etc/systemd/system/aviso.service`:

   .. code-block:: bash

      [Unit]​
      Description=Aviso​
      
      [Service]​
      User=<username> (if omitted it will run as root)
      Group=<groupname> (optional)
      WorkingDirectory= <home_directory> (optional)
      ExecStart=<aviso_location> listen​
      Restart=always
      
      [Install]​
      WantedBy=multi-user.target​

3. Enable the aviso service:

   .. code-block:: console

      % sudo systemctl enable aviso.service​

4. Reload systemd:

   .. code-block:: console

      % sudo systemctl daemon-reload​

5. Start the service:

   .. code-block:: console

      % sudo systemctl start aviso.service

.. note::
   If users change the Aviso configuration, Aviso service must be restarted otherwise the change will be ineffective.


  