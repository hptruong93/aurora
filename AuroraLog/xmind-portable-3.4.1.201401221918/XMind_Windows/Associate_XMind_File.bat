@ECHO OFF

:: Tell the command processor to delay resolution of variables until it executes them.
SETLOCAL ENABLEDELAYEDEXPANSION

:: Correcting current directory when running as administrator:
SETLOCAL ENABLEEXTENSIONS
CD /D "%~dp0"

SET LAUNCHERNAME=XMind
SET CONFIG_TEMPLATE_PATH=%CD%\%LAUNCHERNAME%-assoc.ini
SET CONFIG_FILE_PATH=%CD%\%LAUNCHERNAME%.ini

:: Check whether config template file exists:
IF NOT EXIST "%CONFIG_TEMPLATE_PATH%" GOTO Error101

:: Associate XMind files with the application launcher from the current folder:
FTYPE XMind.Workbook.portable="%CD%\%LAUNCHERNAME%.exe" "%%1"
ASSOC .xmind=XMind.Workbook.portable

:: Rename the old config file in order to protect user custom configs:
SET TIMESTAMP=%DATE:/=-%-%TIME::=-%
SET TIMESTAMP=%TIMESTAMP: =-%
SET CONFIG_BACKUP_PATH=%CD%\%LAUNCHERNAME%_%TIMESTAMP%.ini
MOVE "%CONFIG_FILE_PATH%" "%CONFIG_BACKUP_PATH%"

:: Make a new config file from the template file:
:: Use 'type' to prevent file paths from being splitted by spaces:
FOR /F "tokens=*" %%I IN ('type "%CONFIG_TEMPLATE_PATH%"') DO (
    SET LINE=%%I
    SET LINE=!LINE:@CD@=%CD%!
    ECHO !LINE! >> "%CONFIG_FILE_PATH%"
)

GOTO End


:: No 'XMind-assoc.ini' found error:
:Error101
:: Show error message and exit:
ECHO Error(101): %CONFIG_TEMPLATE_PATH% is not found.
PAUSE
GOTO End


:: End of batch file
:End
