// The Cloud Functions for Firebase SDK to set up triggers and logging.
const {onSchedule} = require("firebase-functions/v2/scheduler");
const {logger} = require("firebase-functions");

const functions = require('firebase-functions');
const admin = require('firebase-admin');

admin.initializeApp();

// Firebase Storage bucket name
const bucketName = "detection-app-f3849"; // Ganti dengan nama bucket Anda

// Maximum number of files to delete in parallel
const MAX_CONCURRENT = 10;

// Run once a day at midnight, to clean up the storage
// Manually run the task here https://console.cloud.google.com/cloudscheduler
exports.storageCleanup = onSchedule("0 0 * * *", async (event) => {
  try {
    // Get a reference to the storage bucket
    const bucket = admin.storage().bucket(bucketName);

    // List all files in the bucket
    const [files] = await bucket.getFiles();

    // Use a promise pool to delete files in parallel with concurrency control
    const promisePool = new PromisePool(
      () => deleteFilesInBatch(files),
      MAX_CONCURRENT
    );
    await promisePool.start();

    logger.log("Storage cleanup finished");
  } catch (error) {
    logger.error("Error during storage cleanup:", error);
  }
});

// Define the node path as the root of the database
const NODE_PATH = '/'; // Root path

exports.scheduledDeleteData = onSchedule("0 0 * * *", async (event) => {
  return admin.database().ref(NODE_PATH).remove()
    .then(() => {
      console.log(`Data deleted from ${NODE_PATH}.`);
      return null; // Scheduled functions should return null or void
    })
    .catch((error) => {
      console.error(`Error deleting data from ${NODE_PATH}.`, error);
      throw new Error('An error occurred while deleting data.');
    });
});

// Function to delete files in batches for efficiency and error handling 
async function deleteFilesInBatch(files) {
  const batchSize = 100; // Number of files per batch, can be adjusted as needed

  for (let i = 0; i < files.length; i += batchSize) {
    const batch = files.slice(i, i + batchSize);
    
    try {
      const deletePromises = batch.map(file => file.delete());
      await Promise.all(deletePromises);
      logger.log(`Deleted batch of ${batch.length} files`);
      
    } catch (err) {
      logger.error(`Error deleting a batch of ${batch.length} files:`, err);
      // Optionally continue or break depending on your failure policy 
    }
  }
}

// PromisePool class controls concurrency when running async tasks in parallel 
class PromisePool {
  constructor(taskGenerator, concurrency) {
    this.taskGenerator = taskGenerator;
    this.concurrency = concurrency;
    
		this.activePromises = new Set();
	}

	async start() {
		const tasksIteratorOrArray= this.taskGenerator();
		
		for(const task of tasksIteratorOrArray){
			const promise=task();
			this.activePromises.add(promise);

			promise.then(() => this.activePromises.delete(promise));

			if(this.activePromises.size >= this.concurrency){
				await Promise.race(this.activePromises);
			}
		}

		await Promise.all(this.activePromises);
	}
}
