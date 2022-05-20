# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

### THIS MUST BE LOCAL IN ALL CONFIGS TO UPDATE ENVIRONMENT ###

import os, sys
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()
logger = sgtk.LogManager.get_logger(__name__)

class PrePublishHook(HookBaseClass):
    """
    This hook defines logic to be executed before showing the publish
    dialog. There may be conditions that need to be checked before allowing
    the user to proceed to publishing.
    """

    @staticmethod
    def _clean_path(path):
        """ Fix slashes, carriage returns and trailing & and ;
        :param path:    <string> path to clean
        :return:        <string> clean path
        """
        path = path.replace(r'\r\n', '')
        path = os.path.normpath(path)
        if path.endswith('&'):
            path = path.rstrip('&')
        if path.endswith(os.pathsep):
            path = path.rstrip(os.pathsep)
        return path

    def _has_envstr(self, env_paths, srch_str):
        """ searches an environment variable to check if an entry has already been added
        :param env_paths: <string>
        :param srch_str: <string>
        :return:
        """
        srch_str = self._clean_path(path=srch_str)
        if not isinstance(env_paths, list):
            env_paths = env_paths.split(os.pathsep) if os.pathsep in env_paths else [env_paths]
        for env_path in env_paths:
            if env_path == '&':
                continue
            env_path = self._clean_path(path=env_path)
            if env_path == srch_str:
                return True
        return False

    def get_pipeline_path(self, package_name, check_version=False, suffix=None):
        """ Checks if the user has a SSVFX_PIPELINE_DEV custom path set, if requested package is not there,
        will find it in the global pipeline directory
        :param package_name:    <string> name of package to locate
        :param check_version:   <bool>
        :param suffix:          <string>
        :return:                <string> path to package
        """
        package_path = None
        root_path = None
        package_name = os.path.normpath(package_name)
        if suffix:
            postfix = suffix
        else:
            postfix = ''

        roots = [os.getenv('SSVFX_PIPELINE_DEV'), os.getenv('SSVFX_PIPELINE')]
        for root_path in roots:
            if not root_path:
                continue
            package_path = os.path.join(root_path, "Pipeline", package_name)
            if os.path.exists(package_path):
                break
            # some things are kept on the same root level as Pipeline, but let's not look there first
            package_path = os.path.join(root_path, package_name)
            if os.path.exists(package_path):
                break
            package_path = None
        if not package_path:
            self.logger.error('Unable to locate %s in Pipeline' % package_name)
            return ''

        # check if it's the new version structure, will have versions and ideally! entry in pipeline_stable_config.json
        if check_version and root_path != os.getenv('SSVFX_PIPELINE_DEV'):
            version = None
            if package_name in self.version_config:
                version = self.version_config.get(package_name)
                self.logger.info('stable %s version set in pipeline config: %s' % (package_name, version))
                if not os.path.exists(os.path.join(package_path, version)):
                    self.logger.warning('requested version has not been released, falling back to latest')
                    version = None
            if not version:
                self.logger.info('finding latest version..')
                version = self.get_latest_package_version(package_path)
            if version:
                return os.path.normpath(os.path.join(package_path, version + postfix))
        return os.path.normpath(package_path + postfix)

    def validate(self):
        """
        Returns True if the user can proceed to publish. Override this hook
        method to execute any custom validation steps.
        """

        # CONSTRUCT BASIC PATHS - all apps use ssvfx_scripts and ssvfx_sg, add that first
        add_paths = [
            self.get_pipeline_path(package_name='ssvfx_scripts'), 
            self.get_pipeline_path(package_name='ssvfx_sg')
            ]

        [sys.path.append(os.path.realpath(i)) for i in add_paths if i not in sys.path]
        self.logger.warning("sys.path: %s" % sys.path)

        return True
        