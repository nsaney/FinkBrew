In this directory, "resources", create a file called BrewPreferences.xml, which should NOT be checked in to source control (as it may have a plaintext password).
Use the rest of this file as a template:
<?xml version="1.0" encoding="UTF-8"?>
<BrewPreferences>
    <Notification>
        <SmtpServer>smtp.gmail.com:587</SmtpServer>
        <SmtpUsername>your.brew.account@gmail.com</SmtpUsername>
        <SmtpPassword>yourBrewAccountPassword</SmtpPassword>
        <FromAddress>your.brew.account@gmail.com</FromAddress>
        <ToAddresses>
          <!-- <ToAddress>some.email.address@gmail.com</ToAddress> -->
          <!-- <ToAddress>4575550100@vtext.com</ToAddress> -->
          <!-- <ToAddress>4575550101@txt.att.net</ToAddress> -->
          <!-- <ToAddress>4575550102@tmomail.net</ToAddress> -->
          <!-- <ToAddress>4575550103@messaging.sprintpcs.com</ToAddress> -->
          <!-- <ToAddress>4575550104@mymetropcs.com</ToAddress> -->
          <!-- and more -->
        </ToAddresses>
        <Notes></Notes>
    </Notification>
</BrewPreferences>