"""
This module configures the installation setup for the laMEG package, facilitating its installation
and post-installation steps.
"""
import site
import os
import glob
import shutil
import subprocess
import sys
import zipfile
from setuptools import setup, find_packages
from setuptools.command.install import install

class CustomInstall(install):
    """
    Custom installation class to handle additional setup tasks for the laMEG package.

    This class extends the standard installation process to include:
    - Installing the SPM (Statistical Parametric Mapping) package.
    - Installing the MATLAB runtime.
    - Setting up necessary environment variables.
    - Downloading and extracting test data.
    - Setting up Jupyter extensions.
    """


    def run(self):
        """
        Executes the custom installation process.

        This method runs the standard installation, installs additional components like
        SPM and MATLAB runtime, sets environment variables, and sets up Jupyter extensions.
        """
        super().run()
        self.install_spm()
        self.install_matlab_runtime()
        self.set_environment_variables()


    def install_spm(self):
        """
        Installs the SPM standalone package.

        This method assembles the SPM standalone package from its parts if not already assembled,
        and installs it using the local setup.py script.
        """
        base_dir = os.path.abspath(os.path.dirname(__file__))
        spm_dir = os.path.join(base_dir, 'spm')
        if not os.path.exists(os.path.join(spm_dir, 'spm_standalone', 'spm_standalone.ctf')):
            os.chdir(os.path.join(spm_dir, 'spm_standalone'))
            subprocess.check_call(['bysp', 'c', 'spm_standalone.ctf'])
            files = glob.glob(os.path.join(spm_dir, 'spm_standalone', 'spm_standalone.ctf.*.part'))
            for file in files:
                os.remove(file)
        os.chdir(spm_dir)
        subprocess.check_call([sys.executable, "setup.py", "install"])
        os.chdir(base_dir)


    def download_file(self, url, save_path):
        """
        Downloads a file from a given URL to the specified path.

        Parameters:
        url (str): The URL to download the file from.
        save_path (str): The local path to save the downloaded file.
        """
        if not os.path.exists(save_path):
            subprocess.check_call(['wget', '-c', url, '-O', save_path])


    def extract_matlab_runtime(self, zip_path, extract_to):
        """
        Extracts the MATLAB runtime from a ZIP file to a specified directory.

        Parameters:
        zip_path (str): The path to the ZIP file containing the MATLAB runtime.
        extract_to (str): The directory to extract the contents to.
        """
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            os.makedirs(extract_to, exist_ok=True)
            zip_ref.extractall(extract_to)
            for root, _, files in os.walk(extract_to):
                for file in files:
                    if file.endswith('.sh') or file == 'install' or 'bin' in root:
                        os.chmod(os.path.join(root, file), 0o755)


    def install_matlab_runtime(self):
        """
        Downloads and installs the MATLAB runtime.

        This method downloads the MATLAB runtime ZIP file, extracts it, and runs the installation
        script in silent mode with the necessary parameters.
        """
        base_dir = os.path.abspath(os.path.dirname(__file__))
        matlab_runtime_zip = os.path.join(base_dir, 'MATLAB_Runtime_R2019a_Update_9_glnxa64.zip')
        matlab_download_url = (
            'https://ssd.mathworks.com/supportfiles/downloads/R2019a/Release/9/'
            'deployment_files/installer/complete/glnxa64/'
            'MATLAB_Runtime_R2019a_Update_9_glnxa64.zip'
        )
        self.download_file(matlab_download_url, matlab_runtime_zip)
        package_dir = self.get_installed_package_dir('spm_standalone')
        matlab_runtime_extract_dir = os.path.join(package_dir, 'matlab_runtime')
        self.extract_matlab_runtime(matlab_runtime_zip, matlab_runtime_extract_dir)

        install_script = os.path.join(matlab_runtime_extract_dir, 'install')
        if not os.path.exists(install_script):
            raise FileNotFoundError(f"The install script was not found in "
                                    f"{matlab_runtime_extract_dir}")

        destination_dir = os.path.join(matlab_runtime_extract_dir, '../../MATLAB_Runtime')
        subprocess.check_call([
            install_script, '-mode', 'silent', '-agreeToLicense', 'yes',
            '-destinationFolder', destination_dir
        ])
        shutil.rmtree(matlab_runtime_extract_dir)


    def set_environment_variables(self):
        """
        Sets environment variables for the MATLAB runtime and Jupyter extensions.

        This method creates activation and deactivation scripts in the Conda environment to manage
        environment variables for the MATLAB runtime and Jupyter extensions.
        """
        matlab_runtime_path = self.get_installed_package_dir('MATLAB_Runtime')

        conda_env_path = os.path.dirname(os.path.dirname(sys.executable))
        activate_script_dir = os.path.join(conda_env_path, "etc", "conda", "activate.d")
        os.makedirs(activate_script_dir, exist_ok=True)
        activate_script_path = os.path.join(activate_script_dir, "env_vars.sh")
        with open(activate_script_path, "w", encoding="utf-8") as out_file:
            out_file.write(f'export MATLAB_RUNTIME_DIR="{matlab_runtime_path}"\n')
            out_file.write('export _OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"\n')
            out_file.write(
                'export LD_LIBRARY_PATH="${MATLAB_RUNTIME_DIR}/v96/runtime/glnxa64:'
                '${MATLAB_RUNTIME_DIR}/v96/bin/glnxa64:'
                '${MATLAB_RUNTIME_DIR}/v96/sys/os/glnxa64:'
                '$LD_LIBRARY_PATH"\n'
            )
            out_file.write('export XAPPLRESDIR="${MATLAB_RUNTIME_DIR}/v96/X11/app-defaults"\n')
            out_file.write('')

        deactivate_script_dir = os.path.join(conda_env_path, "etc", "conda", "deactivate.d")
        os.makedirs(deactivate_script_dir, exist_ok=True)
        deactivate_script_path = os.path.join(deactivate_script_dir, "env_vars.sh")
        with open(deactivate_script_path, "w", encoding="utf-8") as out_file:
            out_file.write('unset MATLAB_RUNTIME_DIR\n')
            out_file.write('export LD_LIBRARY_PATH="$_OLD_LD_LIBRARY_PATH"\n')
            out_file.write('unset _OLD_LD_LIBRARY_PATH\n')
            out_file.write('unset XAPPLRESDIR\n')


    def get_installed_package_dir(self, package_name):
        """
        Finds the installation directory of a specified package.

        Parameters:
        package_name (str): The name of the package to locate.

        Returns:
        str: The path to the installed package.

        Raises:
        FileNotFoundError: If the package is not found in the site-packages directories.
        """
        site_packages = site.getsitepackages()
        for site_package in site_packages:
            potential_path = os.path.join(site_package, package_name)
            if os.path.isdir(potential_path):
                return potential_path
        raise FileNotFoundError(f"Package {package_name} not found in site-packages directories: "
                                f"{site_packages}")


setup(
    name='spm',
    version='0.0.1',
    description='DANC version of SPM compiled as a python library',
    author='DANC lab',
    author_email='james.bonaiuto@isc.cnrs.fr',
    url='https://github.com/danclab/DANC_spm_python',
    packages=find_packages(include=['spm']),
    include_package_data=True,
    cmdclass={
        'install': CustomInstall,
    },
)