.. _historical_notifications:

Dealing with historical notifications
=====================

Before listening to new notifications, Aviso by default checks what was the last notification received and 
it will then return all the notifications that have been missed since. It will then carry on by listening 
to new ones. The first ever time the application runs however no previous notification will be returned. 
This behaviour allows users not to miss any notifications in case of machine reboots.

To override this behaviour by ignoring the missed notifications while listening only to the new ones, 
run the following:

.. code-block:: console

   % aviso listen --now

This command will also reset the notification history.

Users can also explicitly replay past notifications. Aviso can deliver notifications from the ECMWF server 
up to 14 days in the past. This can also be used to test the listener configuration with real notifications.​
Here an example, launch Aviso with the following options:​

.. code-block:: console

   % aviso listen --from 2020-01-20T00:00:00.0Z --to 2020-01-21T00:00:00.0Z

It will replay all the notifications sent from 20 January to 21 January and the ones complying with the listener request will execute the triggers.

.. note::
   Dates must be in the past and ``--to`` can only be defined together with ``--from``. 
   Dates are defined in ISO format and they are in UTC.

In absence of ``--to``, the system after having retrieved the past notifications, it ​will continue listening 
to future notifications. If ``--to`` is defined Aviso will terminate once retrieved all the past notifications.
